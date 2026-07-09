from .base import *
DEBUG = env("DJANGO_DEBUG", default=True)
import sys
if env("USE_SQLITE", default=False, cast=bool) or "pytest" in sys.modules:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
