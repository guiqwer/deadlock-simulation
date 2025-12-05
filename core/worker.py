"""Workers que competem por recursos, com suporte a métricas."""

import multiprocessing as mp
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from core.banker import Banker
from core.logging_utils import log
from core.metrics import Metrics


class Worker(ABC):
    """Interface comum para workers que competem por recursos compartilhados."""

    def __init__(
        self,
        name: str,
        locks: Sequence[Any],
        lock_labels: Sequence[str],
        hold_time: float,
        metrics_queue: Optional[mp.Queue] = None,
    ) -> None:
        self.name = name
        self.locks = list(locks)
        self.lock_labels = list(lock_labels)
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
        acquired: List[int] = []
        try:
            for idx, (lock, label) in enumerate(zip(self.locks, self.lock_labels)):
                self.log(f"precisa do {label}")
                wait_start = time.time()
                lock.acquire()
                self.add_wait_time(time.time() - wait_start)
                acquired.append(idx)
                self.log(f"pegou {label}, trabalhando...")
                time.sleep(self.hold_time)

            self.log("terminou trabalho conjunto, liberando recursos")
            for idx in reversed(acquired):
                self.locks[idx].release()
                self.log(f"liberou {self.lock_labels[idx]}")
            acquired.clear()
            self.record_end("ok")
        except Exception:
            self.record_end("erro")
            raise
        finally:
            # Em caso de erro, libera o que estiver segurando.
            for idx in reversed(acquired):
                try:
                    self.locks[idx].release()
                except Exception:
                    pass


class RetryWorker(Worker):
    """Implementação que evita deadlock com timeout e backoff."""

    def __init__(
        self,
        name: str,
        locks: Sequence[Any],
        lock_labels: Sequence[str],
        hold_time: float,
        try_timeout: float,
        metrics_queue: Optional[mp.Queue] = None,
    ) -> None:
        super().__init__(name, locks, lock_labels, hold_time, metrics_queue)
        self.try_timeout = try_timeout
        self._rng = random.Random(name)

    def run(self) -> None:
        self.record_start()
        try:
            while True:
                acquired: List[int] = []
                failed = False
                for idx, (lock, label) in enumerate(zip(self.locks, self.lock_labels)):
                    self.log(f"precisa do {label}")
                    wait_start = time.time()
                    got = lock.acquire(timeout=self.try_timeout)
                    self.add_wait_time(time.time() - wait_start)
                    if not got:
                        self.increment_retry()
                        self.log(f"timeout aguardando {label}, liberando recursos já segurados")
                        failed = True
                        break
                    acquired.append(idx)
                    self.log(f"pegou {label}, trabalhando...")
                    time.sleep(self.hold_time)

                if not failed and len(acquired) == len(self.locks):
                    self.log("pegou todos os recursos, fazendo o trabalho e liberando")
                    time.sleep(self.hold_time)
                    for idx in reversed(acquired):
                        self.locks[idx].release()
                    self.log("liberou recursos e finalizou sem deadlock")
                    self.record_end("ok")
                    break

                for idx in reversed(acquired):
                    try:
                        self.locks[idx].release()
                    except Exception:
                        pass
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
        super().__init__(name, [], [], hold_time, metrics_queue)
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
