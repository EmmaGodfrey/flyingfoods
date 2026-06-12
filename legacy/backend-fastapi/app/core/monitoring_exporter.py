"""Week 8 exporter adapters that bridge in-process observability to Prometheus."""

from __future__ import annotations

import re
from threading import Lock

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from app.core.observability import log_event, snapshot_raw_metrics

_METRIC_NAME_RE = re.compile(r"[^a-zA-Z0-9_:]")


class PrometheusMetricsExporter:
    """Export in-process counters/histograms to a Prometheus registry via deltas."""

    def __init__(self, registry: CollectorRegistry | None = None, prefix: str = "erp") -> None:
        self.registry = registry or CollectorRegistry(auto_describe=True)
        self.prefix = prefix
        self._lock = Lock()

        self._counter_collectors: dict[str, Counter] = {}
        self._counter_label_names: dict[str, tuple[str, ...]] = {}
        self._counter_last_values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

        self._histogram_collectors: dict[str, Histogram] = {}
        self._histogram_label_names: dict[str, tuple[str, ...]] = {}
        self._histogram_last_index: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}

    def _sanitize_name(self, name: str) -> str:
        normalized = _METRIC_NAME_RE.sub("_", name)
        if not normalized:
            normalized = "metric"
        if normalized[0].isdigit():
            normalized = f"m_{normalized}"
        return f"{self.prefix}_{normalized}"

    def _ensure_counter(self, name: str, label_names: tuple[str, ...]) -> Counter | None:
        existing_labels = self._counter_label_names.get(name)
        if existing_labels is not None and existing_labels != label_names:
            log_event(
                "monitoring.exporter.counter_label_mismatch",
                level="warning",
                metric_name=name,
                expected_labels=existing_labels,
                incoming_labels=label_names,
            )
            return None

        collector = self._counter_collectors.get(name)
        if collector is None:
            metric_base_name = name[:-6] if name.endswith("_total") else name
            collector = Counter(
                self._sanitize_name(metric_base_name),
                documentation=f"Exported counter for {name}",
                labelnames=label_names,
                registry=self.registry,
            )
            self._counter_collectors[name] = collector
            self._counter_label_names[name] = label_names
        return collector

    def _ensure_histogram(self, name: str, label_names: tuple[str, ...]) -> Histogram | None:
        existing_labels = self._histogram_label_names.get(name)
        if existing_labels is not None and existing_labels != label_names:
            log_event(
                "monitoring.exporter.histogram_label_mismatch",
                level="warning",
                metric_name=name,
                expected_labels=existing_labels,
                incoming_labels=label_names,
            )
            return None

        collector = self._histogram_collectors.get(name)
        if collector is None:
            collector = Histogram(
                self._sanitize_name(name),
                documentation=f"Exported histogram for {name}",
                labelnames=label_names,
                registry=self.registry,
            )
            self._histogram_collectors[name] = collector
            self._histogram_label_names[name] = label_names
        return collector

    def collect_from_inprocess(self) -> None:
        """Pull latest in-process metrics and export only new samples."""

        snapshot = snapshot_raw_metrics()

        with self._lock:
            for counter in snapshot["counters"]:
                labels = dict(counter.labels)
                label_names = tuple(labels.keys())
                collector = self._ensure_counter(counter.name, label_names)
                if collector is None:
                    continue

                key = (counter.name, counter.labels)
                previous = self._counter_last_values.get(key, 0.0)
                delta = counter.value - previous
                if delta < 0:
                    # Handles local metric reset/restart without double counting.
                    delta = counter.value
                if delta > 0:
                    collector.labels(**labels).inc(delta)
                self._counter_last_values[key] = counter.value

            for histogram in snapshot["histograms"]:
                labels = dict(histogram.labels)
                label_names = tuple(labels.keys())
                collector = self._ensure_histogram(histogram.name, label_names)
                if collector is None:
                    continue

                key = (histogram.name, histogram.labels)
                previous_index = self._histogram_last_index.get(key, 0)
                if previous_index > len(histogram.values):
                    previous_index = 0

                for value in histogram.values[previous_index:]:
                    collector.labels(**labels).observe(value)
                self._histogram_last_index[key] = len(histogram.values)

    def render_metrics(self) -> str:
        self.collect_from_inprocess()
        return generate_latest(self.registry).decode("utf-8")


_exporter: PrometheusMetricsExporter | None = None
_exporter_lock = Lock()


def get_prometheus_exporter() -> PrometheusMetricsExporter:
    global _exporter
    with _exporter_lock:
        if _exporter is None:
            _exporter = PrometheusMetricsExporter()
        return _exporter
