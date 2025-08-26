import os
from pathlib import Path

import imageio_ffmpeg

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-wa$ou!w9qjx326b+i&*y9v953y&1trk6vbtu(sx@pvp6-n@yga"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['editorapi.smartmediacontrol.com', '127.0.0.1']

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',
    'corsheaders',
    "func",
    'account',
    'rest_framework.authtoken',
    'webpage',
    'export'
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

CLOUDINARY = {
    'cloud_name': "dahqswpxh",
    'api_key': "789826897185359",
    'api_secret': "dgKLPE9gQOXB0LAAi6xnsIsKgOE",
}
# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME':"postgres",
#         'USER': "postgres",
#         'PASSWORD': "oQczjCziRxfMikUuQyjIIGzIoNX0xCDvMPJ0RIqGgsTwNC466YnogF6oxtbA2h1r",
#         'HOST': "147.93.86.127",
#         'PORT': "5436",
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
            "extra_params": "TrustServerCertificate=yes;"
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/


STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = '/var/www/editorBackend/assets/'
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ORIGIN_ALLOW_ALL = True
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Your frontend URL
    "https://editor.smartmediacontrol.com",
]

CORS_ALLOW_METHODS = [
    'GET',
    'OPTIONS',
]
FTP_HOST = "185.183.33.18"
FTP_PORT = 4207
FTP_USER = "ftpLedClip"
FTP_PASS = ":)US8f76Sr"
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'range',  # Important for video streaming
]

AUTH_USER_MODEL = 'account.User'

REST_FRAMEWORK = {

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'account.jwt.JWTAuthentication',
    ],

    'DEFAULT_PAGINATION_CLASS': "rest_framework.pagination.PageNumberPagination",
    'PAGE_SIZE': 12

}
