"""Ponto de entrada do simulador de deadlocks."""

import sys

from cli import main as cli_main

PRESET_ARGS: list[str] | None = [
    "banqueiro", # parametros: deadlock || ordenado || retry || banqueiro || todos
    "--workers",
    "4", # quantidade de processos
    "--progress",
    "--metrics-out",
    "logs/banqueiro.json", 
    "--metrics-format",
    "json", # json || csv
]


def main(argv: list[str] | None = None) -> None:
    effective_args = PRESET_ARGS if PRESET_ARGS is not None else (argv if argv is not None else sys.argv[1:])
    cli_main(effective_args)


if __name__ == "__main__":
    main()
