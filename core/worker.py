"""Workers que competem por recursos, com suporte a métricas."""

import multiprocessing as mp
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from core.banker import Banker
from core.logging_utils import log
from core.metrics import Metrics


class Worker(ABC):
    """Interface comum para workers que competem por recursos compartilhados."""

    def __init__(
        self,
        name: str,
        first_lock: mp.Lock,
        first_label: str,
        second_lock: mp.Lock,
        second_label: str,
        hold_time: float,
        metrics_queue: Optional[mp.Queue] = None,
    ) -> None:
        self.name = name
        self.first_lock = first_lock
        self.first_label = first_label
        self.second_lock = second_lock
        self.second_label = second_label
        self.hold_time = hold_time
        self.metrics_queue = metrics_queue
        self.started_at: float | None = None
        self.retries = 0
        self.wait_time = 0.0

    def log(self, message: str) -> None:
        log(self.name, message)

    def record_start(self) -> None:
        self.started_at = time.time()

    def record_end(self, status: str = "ok") -> None:
        if self.metrics_queue is None:
            return
        ended_at = time.time()
        duration = round(ended_at - self.started_at, 3) if self.started_at else None
        payload: Metrics = {
            "name": self.name,
            "status": status,
            "retries": self.retries,
            "duration": duration,
            "wait_time": round(self.wait_time, 3),
        }
        self.metrics_queue.put(payload)

    def increment_retry(self) -> None:
        self.retries += 1

    def add_wait_time(self, amount: float) -> None:
        self.wait_time += max(0.0, amount)

    @abstractmethod
    def run(self) -> None:
        """Fluxo específico de trabalho de cada cenário."""


class NaiveWorker(Worker):
    """Implementação que pode cair em deadlock."""

    def run(self) -> None:
        self.record_start()
        first_acquired = False
        second_acquired = False
        try:
            self.log(f"precisa do {self.first_label}")
            wait_start = time.time()
            self.first_lock.acquire()
            self.add_wait_time(time.time() - wait_start)
            first_acquired = True

            self.log(f"pegou {self.first_label}, trabalhando...")
            time.sleep(self.hold_time)
            self.log(f"tentando também o {self.second_label}")

            wait_start = time.time()
            self.second_lock.acquire()
            self.add_wait_time(time.time() - wait_start)
            second_acquired = True

            self.log(f"pegou {self.second_label}, terminou trabalho conjunto")
            time.sleep(self.hold_time)
            self.second_lock.release()
            second_acquired = False
            self.log(f"liberou {self.second_label}")

            self.first_lock.release()
            first_acquired = False
            self.log(f"liberou {self.first_label} e finalizou")
            self.record_end("ok")
        except Exception:
            self.record_end("erro")
            raise
        finally:
            if second_acquired:
                self.second_lock.release()
            if first_acquired:
                self.first_lock.release()


class RetryWorker(Worker):
    """Implementação que evita deadlock com timeout e backoff."""

    def __init__(
        self,
        name: str,
        first_lock: mp.Lock,
        first_label: str,
        second_lock: mp.Lock,
        second_label: str,
        hold_time: float,
        try_timeout: float,
        metrics_queue: Optional[mp.Queue] = None,
    ) -> None:
        super().__init__(name, first_lock, first_label, second_lock, second_label, hold_time, metrics_queue)
        self.try_timeout = try_timeout
        self._rng = random.Random(name)

    def run(self) -> None:
        self.record_start()
        try:
            while True:
                self.log(f"precisa do {self.first_label}")
                wait_start = time.time()
                got_first = self.first_lock.acquire(timeout=self.try_timeout)
                self.add_wait_time(time.time() - wait_start)
                if not got_first:
                    self.increment_retry()
                    self.log(f"não conseguiu {self.first_label} em {self.try_timeout}s, tentando de novo")
                    continue

                self.log(f"pegou {self.first_label}, agora quer o {self.second_label}")
                time.sleep(self.hold_time)
                wait_start = time.time()
                got_second = self.second_lock.acquire(timeout=self.try_timeout)
                self.add_wait_time(time.time() - wait_start)

                if got_second:
                    self.log(f"pegou {self.second_label}, fez o trabalho e vai liberar ambos")
                    time.sleep(self.hold_time)
                    self.second_lock.release()
                    self.first_lock.release()
                    self.log("liberou recursos e finalizou sem deadlock")
                    self.record_end("ok")
                    break

                self.increment_retry()
                self.log(f"timeout aguardando {self.second_label}, devolvendo {self.first_label}")
                self.first_lock.release()
                sleep_for = self.hold_time / 2 + self._rng.uniform(0, self.hold_time / 2)
                start_sleep = time.time()
                time.sleep(sleep_for)
                self.add_wait_time(time.time() - start_sleep)
        except Exception:
            self.record_end("erro")
            raise


class BankerWorker(Worker):
    """Worker que negocia recursos com o algoritmo do banqueiro."""

    def __init__(
        self,
        name: str,
        banker: Banker,
        process_id: int,
        claim: List[int],
        resource_labels: List[str],
        hold_time: float,
        metrics_queue: Optional[mp.Queue] = None,
    ) -> None:
        super().__init__(
            name,
            threading.Lock(),
            resource_labels[0],
            threading.Lock(),
            resource_labels[1],
            hold_time,
            metrics_queue,
        )
        self.banker = banker
        self.process_id = process_id
        self.claim = claim
        self.resource_labels = resource_labels
        self.wait_between_attempts = max(0.2, hold_time / 2)
        self._rng = random.Random(name)

    def _build_request(self, remaining: List[int]) -> List[int]:
        """Gera um pedido parcial para evitar monopolizar tudo de uma vez."""
        request: List[int] = []
        for need in remaining:
            if need <= 0:
                request.append(0)
                continue
            request.append(self._rng.randint(1, need))
        if all(value == 0 for value in request):
            idx = self._rng.randrange(len(remaining))
            request[idx] = 1
        return request

    def run(self) -> None:
        self.record_start()
        remaining = list(self.claim)
        try:
            while True:
                request = self._build_request(remaining)
                granted = self.banker.request_resources(self.process_id, request)
                if granted:
                    remaining = [max(need - req, 0) for need, req in zip(remaining, request)]
                    snapshot = self.banker.snapshot()
                    alloc = snapshot["allocation"][self.process_id]
                    available = snapshot["available"]
                    self.log(
                        f"pedido {request} concedido; alocação={alloc} "
                        f"disponível={available}"
                    )
                    if all(value == 0 for value in remaining):
                        self.log("atingiu a necessidade máxima, executando trabalho")
                        time.sleep(self.hold_time)
                        released = self.banker.release_all(self.process_id)
                        self.log(f"liberou recursos {released}")
                        self.record_end("ok")
                        break
                    time.sleep(self.hold_time / 3)
                    continue

                self.increment_retry()
                self.log(
                    f"pedido {request} negado (estado inseguro ou sem recursos), "
                    f"esperando {self.wait_between_attempts:.2f}s"
                )
                wait_for = self.wait_between_attempts + self._rng.uniform(0, self.hold_time / 2)
                start_sleep = time.time()
                time.sleep(wait_for)
                self.add_wait_time(time.time() - start_sleep)
        except Exception:
            self.record_end("erro")
            raise
