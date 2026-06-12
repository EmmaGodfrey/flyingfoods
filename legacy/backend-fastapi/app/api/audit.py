"""Audit log query endpoint with strict branch scoping."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.core.observability import increment_counter, log_event, measure_elapsed_ms, observe_histogram_ms
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.audit import AuditLogListResponse
from app.services.audit_service import list_audit_logs, resolve_audit_branch_scope

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_audit_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    branch_id: int | None = Query(default=None, ge=1),
    actor_user_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    occurred_after: datetime | None = Query(default=None),
    occurred_before: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    request_id = request.headers.get("x-request-id", str(uuid4()))

    started = perf_counter()
    increment_counter("audit_query_requests_total", role=current_user.role)

    try:
        scoped_branch_id = resolve_audit_branch_scope(
            requested_branch_id=branch_id,
            current_user_role=current_user.role,
            current_user_branch_id=current_user.branch_id,
        )
    except PermissionError as exc:
        increment_counter("audit_query_denied_total", role=current_user.role)
        log_event(
            "audit.query.denied",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=current_user.branch_id,
            actor_user_id=current_user.id,
            requested_branch_id=branch_id,
            role=current_user.role,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    items, total = await list_audit_logs(
        session,
        branch_id=scoped_branch_id,
        limit=limit,
        offset=offset,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
    )

    duration_ms = measure_elapsed_ms(started)
    observe_histogram_ms("audit_query_latency_ms", duration_ms, role=current_user.role)
    log_event(
        "audit.query.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=scoped_branch_id,
        actor_user_id=current_user.id,
        role=current_user.role,
        total=total,
        limit=limit,
        offset=offset,
        duration_ms=f"{duration_ms:.2f}",
    )
    return AuditLogListResponse(items=items, total=total, limit=limit, offset=offset)
