"""Development settings: relaxed security, eager Celery optional."""

from config.settings.base import *  # noqa: F401,F403

DEBUG = True

# Tests run against locmem email so PO sends are assertable.
if config("PYTEST_RUNNING", default=False, cast=bool):  # noqa: F405
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
