"""Serializers for authentication and user administration."""

from typing import Any

from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Read shape for user records."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Admin user creation with initial password."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "is_active", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data: dict[str, Any]) -> User:
        """Create the user through the manager so the password gets hashed."""
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Admin user edits; password changes go through a dedicated flow."""

    class Meta:
        model = User
        fields = ["full_name", "role", "is_active"]


class LoginSerializer(serializers.Serializer):
    """Login payload."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
