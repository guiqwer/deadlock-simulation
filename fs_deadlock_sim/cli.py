import argparse

from .scenarios import build_processes_and_resources
from .simulator import Simulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="File System Deadlock Simulator")
    parser.add_argument("--num-processes", "-p", type=int, default=None, help="Number of processes")
    parser.add_argument("--num-resources", "-r", type=int, default=None, help="Number of resources")
    parser.add_argument("--mode", choices=["naive", "ordered"], default="naive", help="Execution mode")
    parser.add_argument("--scenario", choices=["low", "high"], default=None, help="Predefined contention scenarios")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run deterministic demo scenario for fair naive vs ordered comparison",
    )
    parser.add_argument("--max-steps", type=int, default=50, help="Max simulation time steps")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    processes, resources = build_processes_and_resources(
        num_processes=args.num_processes,
        num_resources=args.num_resources,
        scenario=args.scenario,
        demo=args.demo,
        seed=42,
    )

    simulator = Simulator(processes, resources, mode=args.mode, max_steps=args.max_steps)
    simulator.run()


if __name__ == "__main__":
    main()
