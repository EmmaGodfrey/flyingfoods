"""Token issuance and refresh rotation backed by Redis."""

from datetime import timedelta

from redis.asyncio import Redis

from app.core.config import Settings
from app.db.models.user import User
from app.schemas.auth import TokenPair
from app.services.security import create_token, decode_token


async def issue_token_pair(user: User, settings: Settings, redis_client: Redis | None = None) -> TokenPair:
    access_expires = timedelta(minutes=settings.access_token_minutes)
    refresh_expires = timedelta(days=settings.refresh_token_days)

    access_token = create_token(
        subject=str(user.id),
        token_type="access",
        settings=settings,
        expires_delta=access_expires,
        extra_claims={"role": user.role, "branch_id": user.branch_id, "email": user.email},
    )
    refresh_token = create_token(
        subject=str(user.id),
        token_type="refresh",
        settings=settings,
        expires_delta=refresh_expires,
        extra_claims={"role": user.role, "branch_id": user.branch_id, "email": user.email},
    )

    if redis_client is not None:
        refresh_payload = decode_token(refresh_token, settings)
        refresh_ttl = int(refresh_expires.total_seconds())
        await redis_client.setex(f"refresh:{refresh_payload['jti']}", refresh_ttl, str(user.id))

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=int(access_expires.total_seconds()),
        refresh_expires_in=int(refresh_expires.total_seconds()),
    )


async def rotate_refresh_token(refresh_token: str, settings: Settings, redis_client: Redis | None = None) -> tuple[int, str]:
    payload = decode_token(refresh_token, settings)
    if payload.get("type") != "refresh":
        raise ValueError("Expected a refresh token")

    if redis_client is not None:
        key = f"refresh:{payload['jti']}"
        stored_user_id = await redis_client.get(key)
        if stored_user_id is None:
            raise ValueError("Refresh token is no longer valid")
        await redis_client.delete(key)

    return int(payload["sub"]), payload["branch_id"]
