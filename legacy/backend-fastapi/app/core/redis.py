"""Redis dependency provider for API handlers/services."""

from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.core.config import settings


async def get_redis() -> AsyncIterator[Redis | None]:
    # Keep local-dev fallback snappy when Redis is not running.
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=0.1,
        socket_timeout=0.1,
    )
    redis_client: Redis | None = client
    try:
        try:
            await client.ping()
        except Exception:
            # Local/dev fallback when Redis is not available.
            redis_client = None

        yield redis_client
    finally:
        await client.aclose()
