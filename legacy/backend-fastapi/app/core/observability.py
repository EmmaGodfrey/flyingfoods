"""Lightweight observability helpers for structured logs and in-process metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import logging
from threading import Lock
from time import perf_counter
from typing import Any

logger = logging.getLogger("app.observability")


@dataclass(frozen=True, slots=True)
class MetricPoint:
    name: str
    labels: tuple[tuple[str, str], ...]
    value: float


@dataclass(frozen=True, slots=True)
class HistogramPoint:
    name: str
    labels: tuple[tuple[str, str], ...]
    values: tuple[float, ...]


_METRIC_LOCK = Lock()
_COUNTERS: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_HISTOGRAMS: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)


def _normalize_labels(labels: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in labels.items()))


def increment_counter(name: str, amount: float = 1.0, **labels: Any) -> None:
    key = (name, _normalize_labels(labels))
    with _METRIC_LOCK:
        _COUNTERS[key] += amount


def observe_histogram_ms(name: str, value_ms: float, **labels: Any) -> None:
    key = (name, _normalize_labels(labels))
    with _METRIC_LOCK:
        _HISTOGRAMS[key].append(value_ms)


def measure_elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000.0


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    payload = {"event": event, **fields}
    message = " ".join(f"{key}={value}" for key, value in payload.items())
    log_method = getattr(logger, level, logger.info)
    log_method(message)


def snapshot_metrics() -> dict[str, list[MetricPoint]]:
    with _METRIC_LOCK:
        counters = [MetricPoint(name=key[0], labels=key[1], value=value) for key, value in _COUNTERS.items()]
        histograms = [
            MetricPoint(name=key[0], labels=key[1], value=sum(values) / len(values) if values else 0.0)
            for key, values in _HISTOGRAMS.items()
        ]
    return {"counters": counters, "histograms": histograms}


def snapshot_raw_metrics() -> dict[str, list[MetricPoint] | list[HistogramPoint]]:
    """Return immutable copies of internal metric buffers for exporter adapters."""

    with _METRIC_LOCK:
        counters = [MetricPoint(name=key[0], labels=key[1], value=value) for key, value in _COUNTERS.items()]
        histograms = [
            HistogramPoint(name=key[0], labels=key[1], values=tuple(values))
            for key, values in _HISTOGRAMS.items()
        ]
    return {"counters": counters, "histograms": histograms}


def reset_metrics() -> None:
    with _METRIC_LOCK:
        _COUNTERS.clear()
        _HISTOGRAMS.clear()
