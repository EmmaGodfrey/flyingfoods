"""Auth endpoints (login/refresh/logout/me) and admin user management."""

from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.users.permissions import IsAdmin
from apps.users.serializers import (
    LoginSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


def _set_refresh_cookie(response: Response, refresh: RefreshToken) -> None:
    """Attach the refresh token as an httpOnly cookie."""
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
        path="/api/auth/",
    )


class LoginView(APIView):
    """POST /api/auth/login/ — access token in body, refresh in httpOnly cookie."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            raise AuthenticationFailed("Invalid credentials.")
        refresh = RefreshToken.for_user(user)
        response = Response(
            {"access": str(refresh.access_token), "user": UserSerializer(user).data}
        )
        _set_refresh_cookie(response, refresh)
        return response


class RefreshView(APIView):
    """POST /api/auth/refresh/ — rotate the refresh cookie, return a new access."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if not raw:
            raise AuthenticationFailed("No refresh token.")
        try:
            old = RefreshToken(raw)
            user = User.objects.filter(pk=old["user_id"], is_active=True).first()
            if user is None:
                raise AuthenticationFailed("Invalid refresh token.")
            old.blacklist()
        except TokenError as exc:
            raise AuthenticationFailed("Invalid refresh token.") from exc
        refresh = RefreshToken.for_user(user)
        response = Response({"access": str(refresh.access_token)})
        _set_refresh_cookie(response, refresh)
        return response


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklist the refresh token, clear the cookie."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path="/api/auth/")
        return response


class MeView(APIView):
    """GET /api/auth/me/ — the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class UserListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/users/ — admin user management."""

    permission_classes = [IsAdmin]
    filterset_fields = ["role", "is_active"]

    def get_queryset(self):
        """All users, newest first."""
        return User.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        """Create uses the password-bearing serializer."""
        return UserCreateSerializer if self.request.method == "POST" else UserSerializer


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/{id}/ — edit or deactivate; never delete."""

    permission_classes = [IsAdmin]

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_class(self):
        return UserSerializer if self.request.method == "GET" else UserUpdateSerializer
