"""Settings for running the test suite: in-memory cache, fast hashing, no broker."""
from .settings import *  # noqa: F403
from .settings import REST_FRAMEWORK

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = False

LOGGING = {"version": 1, "disable_existing_loggers": True}

REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"auth": "10000/minute", "order_lookup": "10000/minute"}}
