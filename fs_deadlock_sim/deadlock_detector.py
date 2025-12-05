from typing import Dict, List, Optional, Set, Tuple

from .models import Process, ProcessState, Resource


class DeadlockDetector:
    def build_wait_for_graph(self, processes: List[Process], resources: Dict[str, Resource]) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {}
        for process in processes:
            if process.state == ProcessState.BLOCKED and process.current_request:
                holder = resources[process.current_request].held_by
                if holder and holder != process.pid:
                    graph.setdefault(process.pid, set()).add(holder)
        return graph

    def detect_deadlock(self, processes: List[Process], resources: Dict[str, Resource]) -> Tuple[bool, List[Tuple[str, str]], List[str]]:
        graph = self.build_wait_for_graph(processes, resources)
        edges = [(u, v) for u, vs in graph.items() for v in vs]
        cycle = self._find_cycle(graph)
        return (cycle is not None, edges, cycle or [])

    def _find_cycle(self, graph: Dict[str, Set[str]]) -> Optional[List[str]]:
        visited: Set[str] = set()
        stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    found = dfs(neighbor)
                    if found:
                        return found
                elif neighbor in stack:
                    idx = path.index(neighbor)
                    return path[idx:] + [neighbor]
            stack.remove(node)
            path.pop()
            return None

        for node in list(graph.keys()):
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
        return None

    def print_wait_for_graph(self, edges: List[Tuple[str, str]], cycle: List[str]) -> None:
        print("Wait-for graph:")
        if not edges:
            print("  (no edges)")
        else:
            for u, v in edges:
                print(f"  {u} -> {v}")
        if cycle:
            print("  cycle detected: " + " -> ".join(cycle))
