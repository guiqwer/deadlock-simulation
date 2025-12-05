from typing import List

from .models import Process, ProcessState


class MetricsCollector:
    # Collect simple metrics for presentation purposes.
    def __init__(self, mode: str, num_processes: int, num_resources: int):
        self.mode = mode
        self.num_processes = num_processes
        self.num_resources = num_resources
        self.steps = 0
        self.completed = 0
        self.deadlocks = 0
        self.total_wait_time = 0
        self.blocked_steps = 0

    def record_step(self, processes: List[Process]) -> None:
        self.steps += 1
        for process in processes:
            if process.state == ProcessState.BLOCKED:
                self.total_wait_time += 1
                self.blocked_steps += 1
                process.waiting_steps += 1

    def record_completion(self) -> None:
        self.completed += 1

    def record_deadlock(self) -> None:
        self.deadlocks += 1

    def summary(self, processes: List[Process]) -> str:
        total_wait_steps = sum(p.waiting_steps for p in processes)
        blocked_processes = [p for p in processes if p.waiting_steps > 0]
        avg_wait = total_wait_steps / len(blocked_processes) if blocked_processes else 0.0
        blocked_pct = (
            self.blocked_steps / (max(1, self.steps) * len(processes)) * 100
            if processes
            else 0.0
        )
        lines = [
            "Simulation summary:",
            f"  mode: {self.mode}",
            f"  processes: {self.num_processes}",
            f"  resources: {self.num_resources}",
            f"  steps executed: {self.steps}",
            f"  completed processes: {self.completed}",
            f"  deadlocks detected: {self.deadlocks}",
            f"  average waiting time (steps) per blocked process: {avg_wait:.2f}",
            f"  time blocked (%): {blocked_pct:.1f}%",
        ]
        return "\n".join(lines)
