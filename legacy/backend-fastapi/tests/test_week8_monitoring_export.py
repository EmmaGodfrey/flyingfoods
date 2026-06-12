"""Week 8 tests for metrics exporter adapter and monitoring endpoint."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.core.monitoring_exporter import PrometheusMetricsExporter
from app.core.observability import increment_counter, observe_histogram_ms, reset_metrics, snapshot_metrics
from app.main import app


def _metric_value(scrape_text: str, metric_name: str, labels: dict[str, str] | None = None) -> float:
    labels = labels or {}
    escaped_name = re.escape(metric_name)
    if labels:
        label_text = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
        pattern = rf"^{escaped_name}\{{{re.escape(label_text)}\}}\s+([0-9eE.+-]+)$"
    else:
        pattern = rf"^{escaped_name}\s+([0-9eE.+-]+)$"

    match = re.search(pattern, scrape_text, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Metric not found: {metric_name} labels={labels}")
    return float(match.group(1))


def test_prometheus_exporter_exports_deltas_without_double_counting() -> None:
    reset_metrics()
    exporter = PrometheusMetricsExporter(registry=CollectorRegistry(auto_describe=True), prefix="erp")

    increment_counter("event_publish_total", event_type="inventory.write.v1", branch_id=1)
    increment_counter("event_publish_total", event_type="inventory.write.v1", branch_id=1)
    observe_histogram_ms("audit_query_latency_ms", 12.5, role="admin")
    observe_histogram_ms("audit_query_latency_ms", 7.5, role="admin")

    first_scrape = exporter.render_metrics()
    assert (
        _metric_value(
            first_scrape,
            "erp_event_publish_total",
            labels={"branch_id": "1", "event_type": "inventory.write.v1"},
        )
        == 2.0
    )
    assert _metric_value(first_scrape, "erp_audit_query_latency_ms_count", labels={"role": "admin"}) == 2.0

    second_scrape = exporter.render_metrics()
    assert (
        _metric_value(
            second_scrape,
            "erp_event_publish_total",
            labels={"branch_id": "1", "event_type": "inventory.write.v1"},
        )
        == 2.0
    )
    assert _metric_value(second_scrape, "erp_audit_query_latency_ms_count", labels={"role": "admin"}) == 2.0

    increment_counter("event_publish_total", event_type="inventory.write.v1", branch_id=1)
    observe_histogram_ms("audit_query_latency_ms", 20.0, role="admin")

    third_scrape = exporter.render_metrics()
    assert (
        _metric_value(
            third_scrape,
            "erp_event_publish_total",
            labels={"branch_id": "1", "event_type": "inventory.write.v1"},
        )
        == 3.0
    )
    assert _metric_value(third_scrape, "erp_audit_query_latency_ms_count", labels={"role": "admin"}) == 3.0


def test_exporter_does_not_mutate_existing_inprocess_metrics() -> None:
    reset_metrics()
    exporter = PrometheusMetricsExporter(registry=CollectorRegistry(auto_describe=True), prefix="erp")

    increment_counter("audit_query_requests_total", role="admin")
    observe_histogram_ms("audit_query_latency_ms", 10.0, role="admin")

    before = snapshot_metrics()
    exporter.render_metrics()
    after = snapshot_metrics()

    assert before == after


def test_metrics_endpoint_exposes_exported_metrics() -> None:
    reset_metrics()
    increment_counter("audit_query_requests_total", role="admin")

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "erp_audit_query_requests_total" in response.text
