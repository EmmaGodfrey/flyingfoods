"""Global branch-scoped search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_branch, require_role
from app.db.session import get_db
from app.schemas.search import SearchResponse
from app.services.search_service import search_workspace

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer", "cashier"))],
)
async def search_endpoint(
    q: str = Query(min_length=1, max_length=100),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    normalized = q.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query must not be empty")
    return await search_workspace(session, branch_id=branch_id, query=normalized)
