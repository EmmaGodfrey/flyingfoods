"""Week 11 tests for supplier CRUD and branch-scoped search/list behavior."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.models import Branch, Supplier, Unit, User
from app.db.session import get_db
from app.main import app


def _build_test_db() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return session_factory


def _override_db(session_factory: async_sessionmaker[AsyncSession]):
    async def _get_db_override():
        async with session_factory() as session:
            yield session

    return _get_db_override


async def _manager_branch1() -> User:
    return User(id=10, email="manager@example.com", hashed_password="hashed", role="manager", branch_id=1, is_active=True)


async def _manager_branch2() -> User:
    return User(id=20, email="manager2@example.com", hashed_password="hashed", role="manager", branch_id=2, is_active=True)


def _seed_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Branch(id=2, code="BR2", name="Branch 2"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    Unit(id=2, branch_id=2, name="Piece", symbol="pc"),
                    Supplier(id=1, branch_id=1, name="Acme Foods", email="acme@example.com", is_active=True),
                    Supplier(id=2, branch_id=2, name="Other Branch Supplier", email="other@example.com", is_active=True),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def test_supplier_crud_and_search_is_branch_scoped() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _manager_branch1

    try:
        client = TestClient(app)

        created = client.post(
            "/procurement/suppliers",
            json={
                "name": "Fresh Farms",
                "contact_name": "Jane Buyer",
                "phone": "+1-555-1000",
                "email": "fresh@example.com",
                "is_active": True,
            },
        )
        assert created.status_code == 201
        supplier_id = created.json()["supplier_id"]

        listing = client.get("/procurement/suppliers", params={"search": "fresh"})
        assert listing.status_code == 200
        payload = listing.json()
        assert payload["total"] == 1
        assert payload["items"][0]["name"] == "Fresh Farms"

        updated = client.put(f"/procurement/suppliers/{supplier_id}", json={"phone": "+1-555-2222"})
        assert updated.status_code == 200
        assert updated.json()["phone"] == "+1-555-2222"

        deleted = client.delete(f"/procurement/suppliers/{supplier_id}")
        assert deleted.status_code == 204

        listing_after_delete = client.get("/procurement/suppliers", params={"search": "fresh"})
        assert listing_after_delete.status_code == 200
        assert listing_after_delete.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()


def test_supplier_listing_does_not_leak_other_branch() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _manager_branch2

    try:
        client = TestClient(app)
        response = client.get("/procurement/suppliers")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["name"] == "Other Branch Supplier"
    finally:
        app.dependency_overrides.clear()
