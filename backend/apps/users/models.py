"""Custom user model: email authentication, one of eight BRD roles."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.core.models import BaseModel


class UserManager(BaseUserManager):
    """Manager creating users keyed on email."""

    use_in_migrations = True

    def create_user(self, email: str, password: str, **extra_fields) -> "User":
        """Create a regular user with a hashed password."""
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields) -> "User":
        """Create a superuser with the ADMIN role."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("full_name", "Administrator")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """System user. Authenticates via email; role drives every permission."""

    class Role(models.TextChoices):
        CHEF = "CHEF", "Chef"
        WAITER = "WAITER", "Waiter"
        STOREKEEPER = "STOREKEEPER", "Storekeeper"
        RECEIVING_OFFICER = "RECEIVING_OFFICER", "Receiving Officer"
        UNIT_ISSUER = "UNIT_ISSUER", "Unit Issuer"
        RESTAURANT_ISSUER = "RESTAURANT_ISSUER", "Restaurant Issuer"
        MANAGER = "MANAGER", "Manager / Finance"
        ADMIN = "ADMIN", "System Administrator"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CHEF)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"
