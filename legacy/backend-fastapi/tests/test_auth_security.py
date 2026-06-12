"""Unit tests for password hashing and JWT claim integrity."""

from datetime import timedelta

from app.services.security import create_token, decode_token, hash_password, verify_password
from app.core.config import settings


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("super-secret-password")
    assert hashed != "super-secret-password"
    assert verify_password("super-secret-password", hashed)


def test_jwt_roundtrip() -> None:
    token = create_token(
        subject="123",
        token_type="access",
        settings=settings,
        expires_delta=timedelta(minutes=15),
        extra_claims={"role": "manager", "branch_id": 7},
    )
    payload = decode_token(token, settings)
    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert payload["role"] == "manager"
    assert payload["branch_id"] == 7
