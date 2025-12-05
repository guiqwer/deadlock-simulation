from typing import Dict, List, Optional

from .deadlock_detector import DeadlockDetector
from .lock_manager import LockManager
from .metrics import MetricsCollector
from .models import Process, ProcessState, Resource


class Simulator:
    # Main simulation loop with logging, state table, and deadlock detection.
    def __init__(self, processes: List[Process], resources: List[Resource], mode: str, max_steps: int = 50):
        self.processes = processes
        self.resources: Dict[str, Resource] = {r.rid: r for r in resources}
        self.mode = mode
        self.lock_manager = LockManager(self.resources)
        self.detector = DeadlockDetector()
        self.metrics = MetricsCollector(mode, len(processes), len(resources))
        self.max_steps = max_steps

    def run(self) -> None:
        print(f"Running simulation with {len(self.processes)} processes and {len(self.resources)} resources in mode '{self.mode}'")
        deadlock_found = False
        for t in range(self.max_steps):
            deadlock_found = self.step(t)
            self.metrics.record_step(self.processes)
            if deadlock_found:
                break
            if all(p.state == ProcessState.FINISHED for p in self.processes):
                print(f"All processes finished by t={t}")
                break
        print(self.metrics.summary(self.processes))

    def step(self, t: int) -> bool:
        for process in self.processes:
            if process.state in (ProcessState.DEADLOCKED, ProcessState.FINISHED):
                continue
            if process.state == ProcessState.BLOCKED and process.current_request:
                self.lock_manager.request(process, process.current_request, t)
            elif process.state == ProcessState.RUNNING:
                if process.has_all_resources():
                    self._complete_process(process, t)
                    continue
                target = process.next_request(self.mode == "ordered")
                if target:
                    self.lock_manager.request(process, target, t)

        # After acquisition attempts, complete any process that now holds everything
        for process in self.processes:
            if process.state == ProcessState.RUNNING and process.has_all_resources():
                self._complete_process(process, t)

        deadlock, edges, cycle = self.detector.detect_deadlock(self.processes, self.resources)
        self.print_state_table(t)

        if deadlock:
            self.metrics.record_deadlock()
            print(f"*** Deadlock detected at t={t} ***")
            self.detector.print_wait_for_graph(edges, cycle)
            for pid in cycle:
                proc = self._process_by_id(pid)
                if proc:
                    proc.mark_deadlocked()
            return True
        return False

    def _complete_process(self, process: Process, t: int) -> None:
        print(f"[t={t}] {process.pid} completed its work; releasing resources")
        self.lock_manager.release_all(process, t)
        self.metrics.record_completion()

    def _process_by_id(self, pid: str) -> Optional[Process]:
        for process in self.processes:
            if process.pid == pid:
                return process
        return None

    def print_state_table(self, t: int) -> None:
        print("State table:")
        print("  t  | pid | held         | requested   | state")
        for process in self.processes:
            held = ",".join(sorted(process.held_resources)) if process.held_resources else "-"
            requested = process.current_request or "-"
            print(f"  {t:02} | {process.pid:>3} | {held:>11} | {requested:>11} | {process.state.value}")
        print("-")
