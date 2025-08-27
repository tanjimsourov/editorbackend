import os
import shutil
from pathlib import Path

# ───────────────────────────── ffmpeg path ─────────────────────────────
# Prefer env, then system PATH, then fallback. Crash early if not found.
FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
if not os.path.exists(FFMPEG_BIN):
    raise RuntimeError(f"FFMPEG_BIN not found at {FFMPEG_BIN}. Is ffmpeg installed in the container?")

# ───────────────────────────── Paths / base ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────── Security ─────────────────────────────
# (Move secrets to environment variables in production)
SECRET_KEY = "django-insecure-wa$ou!w9qjx326b+i&*y9v953y&1trk6vbtu(sx@pvp6-n@yga"
DEBUG = False
ALLOWED_HOSTS = ["editorapi.smartmediacontrol.com", "127.0.0.1"]

# If you use cookies/CSRF across domains, add your frontends here:
CSRF_TRUSTED_ORIGINS = [
    "https://editor.smartmediacontrol.com",
    "https://editorapi.smartmediacontrol.com",
]

# ───────────────────────────── Apps ─────────────────────────────
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
    "export",
]

# ───────────────────────────── Middleware ─────────────────────────────
# Note: CorsMiddleware appears only once, and early (after SessionMiddleware).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "editorBackend.urls"

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

# ───────────────────────────── Cloudinary (as provided) ─────────────────────────────
# CLOUDINARY = {
#     "cloud_name": "dahqswpxh",
#     "api_key": "789826897185359",
#     "api_secret": "dgKLPE9gQOXB0LAAi6xnsIsKgOE",
# }

# ───────────────────────────── Database (as provided) ─────────────────────────────
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

# ───────────────────────────── Password validation ─────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ───────────────────────────── I18N ─────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ───────────────────────────── Static / Media ─────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = "/var/www/editorBackend/assets/"

# Allow Coolify (or Docker) to override these; fallback to project defaults
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))

# Upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500 MB

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ───────────────────────────── CORS ─────────────────────────────
# Pick ONE strategy:
#  A) explicit origins:
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://editor.smartmediacontrol.com",
]
#  B) or allow all (then remove CORS_ALLOWED_ORIGINS):
# CORS_ORIGIN_ALLOW_ALL = True

# Must allow POST for uploads; include others as needed
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "OPTIONS",
    "PUT",
    "PATCH",
    "DELETE",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "range",  # Important for video streaming
    "content-disposition",
]

# If you use cookie auth across domains:
# CORS_ALLOW_CREDENTIALS = True

# ───────────────────────────── Auth / DRF ─────────────────────────────
AUTH_USER_MODEL = "account.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "account.jwt.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}
