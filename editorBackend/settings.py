import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────── ffmpeg path ─────────────────────────────
# Prefer env, then PATH. Do NOT hardcode a Windows path in Linux.
FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
if not os.path.exists(FFMPEG_BIN):
    # Don’t crash in DEBUG; your views already handle “ffmpeg not found”
    # but keeping this helps you detect bad deployments early.
    # In production you can comment this to avoid hard-fail on boot.
    print(f"[WARN] FFMPEG_BIN not found at {FFMPEG_BIN}. Set FFMPEG_BIN or install ffmpeg.")

# ───────────────────────────── Security ─────────────────────────────
SECRET_KEY = "django-insecure-wa$ou!w9qjx326b+i&*y9v953y&1trk6vbtu(sx@pvp6-n@yga"
DEBUG = True
ALLOWED_HOSTS = ["editorapi.smartmediacontrol.com", "127.0.0.1", "localhost"]

CSRF_TRUSTED_ORIGINS = [
    "https://editor.smartmediacontrol.com",
    "https://editorapi.smartmediacontrol.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "func",
    "account",
    "rest_framework.authtoken",
    "webpage",
    "render",
    "content",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # keep early
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "editorBackend.urls"

# If you’re behind a TLS-terminating proxy (Coolify/nginx), these ensure absolute URLs are HTTPS:
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ───────────────────────────── Assets ─────────────────────────────
ASSET_FALLBACK_DIRS = [
    BASE_DIR / "videos",
    BASE_DIR / "frontend" / "public",
    BASE_DIR / "static",
]
VIDEOS_ROOT = BASE_DIR / "videos"
VIDEOS_URL = "/videos/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "editorBackend.wsgi.application"

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": "editordb",
        "HOST": "185.183.33.18",
        "USER": "editoradmin",
        "PASSWORD": "EQ#f4u7-8@)4",
        "OPTIONS": {
            "driver": "ODBC Driver 18 for SQL Server",
            "extra_params": "TrustServerCertificate=yes;",
        },
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = "/var/www/editorBackend/assets/"

MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))

FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500 MB
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ───────────────────────────── CORS ─────────────────────────────
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://editor.smartmediacontrol.com",
]
# If you serve media completely public, you can open this up later:
# CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_METHODS = [
    "GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE",
]

CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type", "dnt", "origin",
    "user-agent", "x-csrftoken", "x-requested-with",
    "range",               # for byte-range requests
    "content-disposition",
]

# Let the browser read range/length headers (helpful for players)
CORS_EXPOSE_HEADERS = [
    "Content-Length", "Content-Range", "Accept-Ranges",
]

# If you intend to protect media with cookies, then:
# CORS_ALLOW_CREDENTIALS = True
# (and set <video crossOrigin="use-credentials">). For public media keep it False.

# ───────────────────────────── Auth / DRF ─────────────────────────────
AUTH_USER_MODEL = "account.User"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "account.jwt.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}
