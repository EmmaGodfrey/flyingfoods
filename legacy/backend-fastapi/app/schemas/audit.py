"""Audit log query and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    actor_user_id: int | None
    branch_id: int
    action: str
    entity_type: str
    entity_id: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    request_id: str | None
    source: str
    schema_version: int
    hash_chain_prev: str | None
    hash_chain_curr: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int


class AuditLogFilter(BaseModel):
    branch_id: int | None = Field(default=None, ge=1)
    actor_user_id: int | None = Field(default=None, ge=1)
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    occurred_after: datetime | None = None
    occurred_before: datetime | None = None
