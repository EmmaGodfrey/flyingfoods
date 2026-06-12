"""Audit service for immutable write logs and query filtering."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import DomainEvent
from app.db.models.audit_log import AuditLog

AUDIT_SCHEMA_VERSION = 1
INVENTORY_WRITE_EVENT = "inventory.write.v1"


def to_audit_json(data: dict[str, Any] | None) -> str:
    return json.dumps(data or {}, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash_chain(prev_hash: str | None, payload: dict[str, Any]) -> str:
    serialized_payload = to_audit_json(payload)
    source = f"{prev_hash or ''}|{serialized_payload}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


async def create_audit_log(
    session: AsyncSession,
    *,
    actor_user_id: int | None,
    branch_id: int,
    action: str,
    entity_type: str,
    entity_id: str,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    request_id: str | None,
    source: str,
    occurred_at: datetime,
) -> AuditLog:
    previous_hash_stmt = (
        select(AuditLog.hash_chain_curr)
        .where(AuditLog.branch_id == branch_id)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    previous_hash = (await session.execute(previous_hash_stmt)).scalar_one_or_none()

    hash_payload = {
        "occurred_at": occurred_at.isoformat(),
        "actor_user_id": actor_user_id,
        "branch_id": branch_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_json": before_json,
        "after_json": after_json,
        "request_id": request_id,
        "source": source,
        "schema_version": AUDIT_SCHEMA_VERSION,
    }

    log = AuditLog(
        occurred_at=occurred_at,
        actor_user_id=actor_user_id,
        branch_id=branch_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before_json,
        after_json=after_json,
        request_id=request_id,
        source=source,
        schema_version=AUDIT_SCHEMA_VERSION,
        hash_chain_prev=previous_hash,
        hash_chain_curr=compute_hash_chain(previous_hash, hash_payload),
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def write_audit_log_from_event(event: DomainEvent, context: dict[str, Any]) -> None:
    session = context.get("session")
    if session is None:
        return

    payload = event.payload
    await create_audit_log(
        session,
        actor_user_id=payload.get("actor_user_id"),
        branch_id=event.branch_id,
        action=payload["action"],
        entity_type=payload["entity_type"],
        entity_id=str(payload["entity_id"]),
        before_json=payload.get("before_json"),
        after_json=payload.get("after_json"),
        request_id=event.correlation_id,
        source=payload.get("source", "api"),
        occurred_at=event.occurred_at,
    )


def resolve_audit_branch_scope(*, requested_branch_id: int | None, current_user_role: str, current_user_branch_id: int) -> int:
    elevated_roles = {"superadmin", "admin"}
    if current_user_role in elevated_roles:
        return requested_branch_id if requested_branch_id is not None else current_user_branch_id

    if requested_branch_id is not None and requested_branch_id != current_user_branch_id:
        raise PermissionError("Cross-branch audit access denied")

    return current_user_branch_id


async def list_audit_logs(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    actor_user_id: int | None,
    action: str | None,
    entity_type: str | None,
    entity_id: str | None,
    occurred_after: datetime | None,
    occurred_before: datetime | None,
) -> tuple[list[AuditLog], int]:
    filters: list[Any] = [AuditLog.branch_id == branch_id]
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if occurred_after is not None:
        filters.append(AuditLog.occurred_at >= occurred_after)
    if occurred_before is not None:
        filters.append(AuditLog.occurred_at <= occurred_before)

    where_clause = and_(*filters)

    count_stmt = select(func.count()).select_from(AuditLog).where(where_clause)
    total = int((await session.execute(count_stmt)).scalar_one())

    stmt = (
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.execute(stmt)).scalars().all()
    return list(items), total
