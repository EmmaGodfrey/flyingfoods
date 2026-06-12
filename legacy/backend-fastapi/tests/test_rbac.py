"""Tests for role-based access dependency behavior."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_role
from app.db.models.branch import Branch
from app.db.models.user import User


async def override_current_user() -> User:
    branch = Branch(id=1, code="HQ", name="Headquarters")
    return User(
        id=1,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=branch.id,
        is_active=True,
        branch=branch,
    )


def test_require_role_denies_wrong_role() -> None:
    app = FastAPI()

    @app.get("/manager-only")
    async def manager_only(_user=Depends(require_role("manager", "admin"))):
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/manager-only")
    assert response.status_code == 401


def test_require_role_allows_manager() -> None:
    app = FastAPI()
    app.dependency_overrides.clear()

    @app.get("/manager-only")
    async def manager_only(_user=Depends(require_role("manager", "admin"))):
        return {"ok": True}

    from app.api.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.get("/manager-only")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
