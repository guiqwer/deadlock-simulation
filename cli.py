"""Parser de argumentos e execução dos cenários."""

import argparse
import sys
from typing import List

from config import DEADLOCK_TIMEOUT, DEFAULT_RETRY_TIMEOUT, HOLD_TIME
from core.logging_utils import configure_multiprocessing
from core.metrics import Metrics, export_metrics
from core.scenario import BankerScenario, DeadlockScenario, OrderedScenario, RetryScenario


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demonstração de deadlock e soluções com processos concorrentes."
    )

    def positive_int(value: str) -> int:
        ivalue = int(value)
        if ivalue < 1:
            raise argparse.ArgumentTypeError("use um inteiro >= 1")
        return ivalue

    parser.add_argument(
        "cenario",
        nargs="?",
        default="todos",
        choices=["todos", "deadlock", "ordenado", "retry", "banqueiro"],
        help="Qual cenário rodar (padrão: todos em sequência).",
    )
    parser.add_argument(
        "--metrics-out",
        dest="metrics_out",
        help="Caminho para salvar métricas (JSON ou CSV).",
    )
    parser.add_argument(
        "--metrics-format",
        dest="metrics_format",
        choices=["json", "csv"],
        default="json",
        help="Formato de métricas ao salvar (padrão: json).",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Exibe progresso simples de conclusão dos workers.",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=positive_int,
        default=2,
        help="Quantidade de processos a lançar em cada cenário (padrão: 2).",
    )
    parser.add_argument(
        "--resources",
        "-r",
        type=positive_int,
        default=2,
        help="Quantidade de recursos compartilhados (padrão: 2).",
    )
    parser.add_argument(
        "--resource-units",
        "-u",
        type=positive_int,
        default=1,
        help="Quantidade de unidades por recurso (aplicável ao banqueiro, padrão: 1).",
    )
    return parser.parse_args(argv)


def run_selected_scenarios(
    selected: str,
    metrics_out: str | None,
    metrics_format: str,
    show_progress: bool,
    workers: int,
    resources: int,
    resource_units: int,
) -> None:
    scenarios = {
        "deadlock": DeadlockScenario(HOLD_TIME, DEADLOCK_TIMEOUT, show_progress, workers, resource_count=resources),
        "ordenado": OrderedScenario(HOLD_TIME, show_progress, workers, resource_count=resources),
        "retry": RetryScenario(HOLD_TIME, try_timeout=DEFAULT_RETRY_TIMEOUT, show_progress=show_progress, workers=workers, resource_count=resources),
        "banqueiro": BankerScenario(HOLD_TIME, show_progress, workers, resource_count=resources, resource_units=resource_units),
    }
    all_metrics: List[Metrics] = []

    if selected == "todos":
        for key in ("deadlock", "ordenado", "retry", "banqueiro"):
            all_metrics.extend(scenarios[key].run())
    else:
        all_metrics.extend(scenarios[selected].run())

    if metrics_out:
        export_metrics(all_metrics, metrics_out, metrics_format)


def main(argv: List[str]) -> None:
    configure_multiprocessing()
    args = parse_args(argv)
    run_selected_scenarios(
        args.cenario,
        args.metrics_out,
        args.metrics_format,
        args.progress,
        args.workers,
        args.resources,
        args.resource_units,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
