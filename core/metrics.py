"""Coleta, sumarização e exportação de métricas."""

import csv
import json
import multiprocessing as mp
from pathlib import Path
from typing import Any, Dict, List

Metrics = Dict[str, Any]


def create_metrics_queue() -> mp.Queue | None:
    """Cria a fila de métricas ou desativa telemetria se não houver permissão."""
    try:
        return mp.Queue()
    except PermissionError:
        print("[RESUMO] Telemetria desativada: sem permissão para criar fila de métricas.")
        return None


def collect_metrics(metrics_queue: mp.Queue | None) -> List[Metrics]:
    """Coleta métricas acumuladas na fila."""
    if metrics_queue is None:
        return []
    metrics: List[Metrics] = []
    while not metrics_queue.empty():
        try:
            metrics.append(metrics_queue.get_nowait())
        except Exception:
            break
    return metrics


def summarize_metrics(metrics: List[Metrics], duration: float, process_names: List[str], scenario_tag: str) -> None:
    """Imprime resumo com métricas individuais e médias."""
    if not metrics:
        return

    print("[RESUMO] Tempo total do cenário: "
          f"{round(duration, 3)}s (inclui criação/enceramento de processos).")
    for metric in metrics:
        name = metric.get("name", "?")
        status = metric.get("status", "desconhecido")
        retries = metric.get("retries")
        metric_duration = metric.get("duration")
        wait_time = metric.get("wait_time")
        duration_text = f"{metric_duration:.3f}s" if metric_duration is not None else "n/d"
        retries_text = retries if retries is not None else 0
        wait_text = f"{wait_time:.3f}s" if wait_time is not None else "n/d"
        print(f" - {name}: status={status}, duração={duration_text}, espera={wait_text}, retries={retries_text}")

    reported = {metric.get("name") for metric in metrics}
    missing = [name for name in process_names if name not in reported]
    if missing:
        print(f" - Sem telemetria (interrompidos?): {missing}")

    def average(numbers: List[float]) -> float | None:
        valid = [n for n in numbers if n is not None]
        return sum(valid) / len(valid) if valid else None

    avg_retries = average([metric.get("retries") for metric in metrics if isinstance(metric.get("retries"), (int, float))])  # type: ignore[arg-type]
    avg_duration = average([metric.get("duration") for metric in metrics if isinstance(metric.get("duration"), (int, float))])  # type: ignore[arg-type]
    avg_wait_time = average([metric.get("wait_time") for metric in metrics if isinstance(metric.get("wait_time"), (int, float))])  # type: ignore[arg-type]
    if avg_retries is not None:
        print(f"[{scenario_tag}] Média de retries: {avg_retries:.1f}")
    if avg_duration is not None:
        print(f"[{scenario_tag}] Tempo total médio: {avg_duration:.2f}s")
    if avg_wait_time is not None:
        print(f"[{scenario_tag}] Tempo médio aguardando recurso: {avg_wait_time:.2f}s")
    print()


def export_metrics(metrics: List[Metrics], path_str: str, fmt: str) -> None:
    """Salva métricas em JSON ou CSV."""
    if not metrics:
        print(f"[RESUMO] Nenhuma métrica coletada; não gerei {path_str}.")
        return

    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        with path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    else:
        fieldnames = sorted({key for metric in metrics for key in metric.keys()})
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics)

    print(f"[RESUMO] Métricas exportadas para {path} ({fmt}).")
