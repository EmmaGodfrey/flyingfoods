"""JWT authentication middleware for Channels websockets.

Clients connect with `?token=<access>` since browsers cannot set headers
on WebSocket upgrade requests.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(token: str):
    """Resolve an access token to an active user, or AnonymousUser."""
    from apps.users.models import User

    try:
        payload = AccessToken(token)
        return User.objects.filter(pk=payload["user_id"], is_active=True).first() or AnonymousUser()
    except (InvalidToken, TokenError, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Populate scope['user'] from the access token in the query string."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        scope["user"] = await _get_user(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
