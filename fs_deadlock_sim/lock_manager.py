from typing import Dict

from .models import Process, ProcessState, Resource


class LockManager:
    # Simple lock manager for exclusive resource ownership.
    def __init__(self, resources: Dict[str, Resource]):
        self.resources = resources

    def request(self, process: Process, resource_id: str, t: int) -> bool:
        resource = self.resources[resource_id]
        if resource.held_by is None:
            resource.held_by = process.pid
            process.held_resources.add(resource_id)
            process.state = ProcessState.RUNNING
            process.current_request = None
            print(f"[t={t}] {process.pid} acquired {resource_id}")
            return True
        if resource.held_by == process.pid:
            return True
        process.mark_blocked(resource_id)
        print(f"[t={t}] {process.pid} requested {resource_id} but it is held by {resource.held_by}; BLOCKED")
        return False

    def release_all(self, process: Process, t: int) -> None:
        if process.held_resources:
            held = ", ".join(sorted(process.held_resources))
            print(f"[t={t}] {process.pid} releasing {held}")
        for res_id in list(process.held_resources):
            resource = self.resources[res_id]
            if resource.held_by == process.pid:
                resource.held_by = None
        process.held_resources.clear()
        process.current_request = None
        process.state = ProcessState.FINISHED
