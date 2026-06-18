"""Production settings: hardened defaults, fail loudly on misconfiguration."""

from decouple import config

from config.settings.base import *  # noqa: F401,F403

DEBUG = False

if config("DJANGO_DEBUG", default=False, cast=bool):
    raise RuntimeError("DJANGO_DEBUG=True must never reach production.")

if SECRET_KEY == "dev-insecure-secret-change-me":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
COOKIE_SECURE = config("DJANGO_COOKIE_SECURE", default=True, cast=bool)
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SECURE = COOKIE_SECURE
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
