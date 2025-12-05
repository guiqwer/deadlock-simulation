import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set


class ProcessState(Enum):
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    DEADLOCKED = "DEADLOCKED"
    FINISHED = "FINISHED"


@dataclass
class Resource:
    rid: str
    held_by: Optional[str] = None


@dataclass
class Process:
    pid: str
    plan: List[str]
    held_resources: Set[str] = field(default_factory=set)
    current_request: Optional[str] = None
    state: ProcessState = ProcessState.RUNNING
    waiting_steps: int = 0

    def next_request(self, ordered_mode: bool) -> Optional[str]:
        # Return next resource to request respecting mode.
        if self.state in (ProcessState.BLOCKED, ProcessState.DEADLOCKED, ProcessState.FINISHED):
            return None
        remaining = [r for r in self.plan if r not in self.held_resources]
        if not remaining:
            return None
        if ordered_mode:
            return sorted(remaining)[0]
        # naive: respect declared plan order for determinism
        for resource_id in self.plan:
            if resource_id not in self.held_resources:
                return resource_id
        return None

    def has_all_resources(self) -> bool:
        return all(r in self.held_resources for r in self.plan)

    def mark_blocked(self, resource_id: str) -> None:
        self.state = ProcessState.BLOCKED
        self.current_request = resource_id

    def mark_deadlocked(self) -> None:
        self.state = ProcessState.DEADLOCKED

    def reset_blocking(self) -> None:
        self.current_request = None
        if self.state == ProcessState.BLOCKED:
            self.state = ProcessState.RUNNING
