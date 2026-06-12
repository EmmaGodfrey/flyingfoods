"""Schemas for branch-scoped global search responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    item_type: str
    item_id: str
    title: str
    subtitle: str | None = None
    route: str | None = None
    highlights: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str = Field(min_length=1, max_length=100)
    branch_id: int
    total: int
    products: list[SearchResultItem]
    suppliers: list[SearchResultItem]
    invoices: list[SearchResultItem]
