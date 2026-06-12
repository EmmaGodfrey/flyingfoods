"""Monitoring scrape endpoint for Prometheus."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.monitoring_exporter import get_prometheus_exporter

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", include_in_schema=False)
async def get_metrics() -> Response:
    exporter = get_prometheus_exporter()
    payload = exporter.render_metrics()
    return Response(content=payload, media_type="text/plain; version=0.0.4; charset=utf-8")
