import random
from typing import List, Optional, Tuple

from .models import Process, Resource


def make_resources(num_resources: int) -> List[Resource]:
    return [Resource(rid=f"R{i + 1}") for i in range(num_resources)]


def demo_scenario() -> Tuple[List[Process], List[Resource]]:
    # Deterministic scenario to compare naive vs ordered.
    resources = make_resources(2)
    processes = [
        Process(pid="P1", plan=["R1", "R2"]),
        Process(pid="P2", plan=["R2", "R1"]),
        Process(pid="P3", plan=["R1"]),
    ]
    return processes, resources


def build_processes_and_resources(
    num_processes: Optional[int],
    num_resources: Optional[int],
    scenario: Optional[str],
    demo: bool,
    seed: int = 42,
) -> Tuple[List[Process], List[Resource]]:
    if demo:
        random.seed(seed)
        return demo_scenario()

    if scenario == "low":
        num_processes = num_processes or 3
        num_resources = num_resources or 10
    elif scenario == "high":
        num_processes = num_processes or 10
        num_resources = num_resources or 3
    else:
        num_processes = num_processes or 5
        num_resources = num_resources or 5

    resources = make_resources(num_resources)
    res_ids = [r.rid for r in resources]
    processes: List[Process] = []

    # Seed fixed for repeatable demonstrations when a scenario is chosen
    random.seed(seed if scenario else None)

    for i in range(num_processes):
        need_count = 2 if num_resources >= 2 else 1
        plan = random.sample(res_ids, k=min(need_count, len(res_ids)))
        processes.append(Process(pid=f"P{i + 1}", plan=plan))

    return processes, resources
