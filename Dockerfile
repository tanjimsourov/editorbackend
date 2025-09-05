# Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ---------- System deps (ffmpeg + fonts + useful libs) ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ffmpeg \
      fontconfig fonts-dejavu \
      poppler-utils \
      curl gnupg ca-certificates apt-transport-https \
      unixodbc unixodbc-dev \
  && rm -rf /var/lib/apt/lists/*

# ---------- (Optional) Microsoft ODBC Driver 18 ----------
ARG INSTALL_MSODBCSQL18=1
RUN if [ "$INSTALL_MSODBCSQL18" = "1" ]; then \
      curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
      echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/microsoft-prod.list && \
      apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# LibODBC soname safety net (no-op if .so.2 already exists)
RUN test -e /usr/lib/x86_64-linux-gnu/libodbc.so.2 || \
    ln -s /usr/lib/x86_64-linux-gnu/libodbc.so /usr/lib/x86_64-linux-gnu/libodbc.so.2 || true

# ---------- Runtime ENV ----------
ENV FFMPEG_BIN=/usr/bin/ffmpeg \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    MEDIA_ROOT=/app/media \
    MEDIA_URL=/media/

# Prove ffmpeg exists at build time (early failure if base image changes)
RUN ffmpeg -hide_banner -version && which ffmpeg

# ---------- Create non-root user & prepare writable paths ----------
RUN useradd -m appuser && \
    mkdir -p /var/www && chown -R appuser:appuser /var/www && \
    mkdir -p /app && chown -R appuser:appuser /app

# ---------- Python deps ----------
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# ---------- App code ----------
COPY . /app/
RUN chown -R appuser:appuser /app

# ---------- Drop privileges ----------
USER appuser

EXPOSE 8003

# ---------- Entrypoint / CMD ----------
# What this does at runtime:
# 1) Recreate MEDIA_ROOT every start (you said you removed /app/media).
# 2) Detect the actual STATIC_ROOT from Django settings and mkdir -p it.
# 3) Run migrations and collectstatic safely for Coolify.
CMD bash -lc '\
  set -euo pipefail; \
  echo "Ensuring MEDIA_ROOT at: ${MEDIA_ROOT}"; \
  mkdir -p "${MEDIA_ROOT}"; \
  \
  echo "Discovering STATIC_ROOT from Django settings..."; \
  PY_STATIC_DIR=$(python - <<PY \
import sys, pathlib; \
from django.conf import settings; \
print(pathlib.Path(getattr(settings, "STATIC_ROOT", "/var/www/static")).as_posix()) \
PY
  ); \
  echo "STATIC_ROOT resolved to: ${PY_STATIC_DIR}"; \
  # Make sure parent of STATIC_ROOT is writable (handles deep /var/www/... paths)
  mkdir -p "${PY_STATIC_DIR}"; \
  \
  echo "Running Django migrations..."; \
  python manage.py makemigrations --noinput || true; \
  python manage.py migrate --noinput; \
  \
  echo "Collecting static files into: ${PY_STATIC_DIR}"; \
  python manage.py collectstatic --noinput; \
  \
  echo "Starting Gunicorn..."; \
  python -m gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
'
