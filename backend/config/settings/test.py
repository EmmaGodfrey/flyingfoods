"""Test settings: SQLite, in-memory channels and cache, locmem email.

Lets the suite run without Postgres or Redis. CI may instead point
DJANGO_SETTINGS_MODULE at config.settings.dev with real services.
"""

from config.settings.base import *  # noqa: F401,F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
