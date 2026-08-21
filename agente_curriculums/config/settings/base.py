from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    MAX_PDF_SIZE_MB=(int, 15),
    WHATSAPP_VALIDATE_SIGNATURE=(bool, True),
    WHATSAPP_MAX_DOCUMENT_SIZE_MB=(int, 15),
    WHATSAPP_WEBHOOK_MAX_BODY_KB=(int, 512),
    IMAP_PORT=(int, 993),
    IMAP_USE_SSL=(bool, True),
    IMAP_MARK_AS_READ=(bool, True),
    ANALYSIS_INTERVAL_SECONDS=(int, 900),
    ANALYSIS_BATCH_SIZE=(int, 2),
    OLLAMA_TIMEOUT_SECONDS=(int, 600),
    PUBLIC_FORM_MAX_PDF_SIZE_MB=(int, 10),
    PUBLIC_FORM_RATE_LIMIT=(int, 5),
    PUBLIC_FORM_IP_RATE_LIMIT=(int, 20),
    PUBLIC_FORM_RATE_WINDOW_SECONDS=(int, 3600),
    PRIVACY_NOTICE_URL=(str, ""),
    TURNSTILE_ENABLED=(bool, False),
    PDF_ANTIVIRUS_ENABLED=(bool, False),
    CLAMAV_PORT=(int, 3310),
)
environ.Env.read_env(BASE_DIR / ".env")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-only")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "rest_framework", "django_filters", "documentos", "integraciones", "analisis", "vacantes", "postulaciones"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.mysql", "NAME": env("DATABASE_NAME", default="agente_curriculums"), "USER": env("DATABASE_USER", default="agente_user"), "PASSWORD": env("DATABASE_PASSWORD", default="change_me"), "HOST": env("DATABASE_HOST", default="127.0.0.1"), "PORT": env("DATABASE_PORT", default="3306"), "OPTIONS": {"charset": "utf8mb4"}}}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MAX_PDF_SIZE_MB = env("MAX_PDF_SIZE_MB")
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"], "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"], "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend", "rest_framework.filters.SearchFilter", "rest_framework.filters.OrderingFilter"], "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 20}
MICROSOFT_TENANT_ID = env("MICROSOFT_TENANT_ID", default="")
MICROSOFT_CLIENT_ID = env("MICROSOFT_CLIENT_ID", default="")
MICROSOFT_CLIENT_SECRET = env("MICROSOFT_CLIENT_SECRET", default="")
MICROSOFT_MAILBOX = env("MICROSOFT_MAILBOX", default="")
IMAP_HOST = env("IMAP_HOST", default="")
IMAP_PORT = env("IMAP_PORT")
IMAP_USERNAME = env("IMAP_USERNAME", default="")
IMAP_PASSWORD = env("IMAP_PASSWORD", default="")
IMAP_FOLDER = env("IMAP_FOLDER", default="INBOX")
IMAP_USE_SSL = env("IMAP_USE_SSL")
IMAP_MARK_AS_READ = env("IMAP_MARK_AS_READ")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://127.0.0.1:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", default="gemma4:e2b-it-qat")
OLLAMA_TIMEOUT_SECONDS = env("OLLAMA_TIMEOUT_SECONDS")
ANALYSIS_INTERVAL_SECONDS = env("ANALYSIS_INTERVAL_SECONDS")
ANALYSIS_BATCH_SIZE = env("ANALYSIS_BATCH_SIZE")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_BUSINESS_ACCOUNT_ID = env("WHATSAPP_BUSINESS_ACCOUNT_ID", default="")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_GRAPH_VERSION = env("WHATSAPP_GRAPH_VERSION", default=env("WHATSAPP_API_VERSION", default=""))
WHATSAPP_API_VERSION = WHATSAPP_GRAPH_VERSION
WHATSAPP_VALIDATE_SIGNATURE = env("WHATSAPP_VALIDATE_SIGNATURE")
WHATSAPP_MAX_DOCUMENT_SIZE_MB = env("WHATSAPP_MAX_DOCUMENT_SIZE_MB")
WHATSAPP_WEBHOOK_MAX_BODY_KB = env("WHATSAPP_WEBHOOK_MAX_BODY_KB")
PUBLIC_FORM_MAX_PDF_SIZE_MB = env("PUBLIC_FORM_MAX_PDF_SIZE_MB")
PUBLIC_FORM_RATE_LIMIT = env("PUBLIC_FORM_RATE_LIMIT")
PUBLIC_FORM_IP_RATE_LIMIT = env("PUBLIC_FORM_IP_RATE_LIMIT")
PUBLIC_FORM_RATE_WINDOW_SECONDS = env("PUBLIC_FORM_RATE_WINDOW_SECONDS")
PRIVACY_NOTICE_URL = env("PRIVACY_NOTICE_URL")
TURNSTILE_ENABLED = env("TURNSTILE_ENABLED")
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
PDF_ANTIVIRUS_ENABLED = env("PDF_ANTIVIRUS_ENABLED")
CLAMAV_HOST = env("CLAMAV_HOST", default="127.0.0.1")
CLAMAV_PORT = env("CLAMAV_PORT")
LOGGING = {"version": 1, "disable_existing_loggers": False, "formatters": {"standard": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}}, "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}}, "root": {"handlers": ["console"], "level": "INFO"}}
