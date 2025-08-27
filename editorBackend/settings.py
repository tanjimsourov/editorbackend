# settings.py
import os
import shutil
from pathlib import Path

# --- ffmpeg path: prefer env, fallback to system path ---
FFMPEG_BIN = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
if not os.path.exists(FFMPEG_BIN):
    raise RuntimeError(f"FFMPEG_BIN not found at {FFMPEG_BIN}. Is ffmpeg installed in the container?")

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
SECRET_KEY = "django-insecure-..."  # consider moving to env
DEBUG = False
ALLOWED_HOSTS = ['editorapi.smartmediacontrol.com', '127.0.0.1']

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

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",    # ✅ once, and early (right after SessionMiddleware)
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

# --- DATABASES (unchanged) ---
# ... your existing DB config ...

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
STATIC_URL = "static/"
STATIC_ROOT = "/var/www/editorBackend/assets/"

# Let Docker/Coolify override these if desired
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))

# Upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS (fix methods; avoid duplicates) ---
# Choose ONE approach:
# A) Allow-list origins:
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://editor.smartmediacontrol.com",
    # add any other frontend origins here
]
# OR B) allow all (then remove CORS_ALLOWED_ORIGINS entirely)
# CORS_ORIGIN_ALLOW_ALL = True

# Crucial: allow POST for uploads
CORS_ALLOW_METHODS = [
    "GET",
    "POST",     # ✅ required for /save-video
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
    "range",
]

# If your frontend is on a different domain and you use cookies, also consider:
# CORS_ALLOW_CREDENTIALS = True

AUTH_USER_MODEL = "account.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "account.jwt.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}
