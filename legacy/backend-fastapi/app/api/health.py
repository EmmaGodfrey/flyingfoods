"""System health endpoints for readiness/liveness checks."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
