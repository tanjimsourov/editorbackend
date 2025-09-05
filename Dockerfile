# Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ---------- System deps (ffmpeg + fonts + useful libs) ----------
# - ffmpeg: required for preview/export (H.264/AAC enabled on Debian 12 builds)
# - fontconfig & fonts-dejavu: avoid ffmpeg "font not found" errors for drawtext
# - poppler-utils: if you ever rasterize PDFs as assets
# - curl/gnupg/ca-certificates: for optional MS ODBC install step
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ffmpeg \
      fontconfig fonts-dejavu \
      poppler-utils \
      curl gnupg ca-certificates apt-transport-https \
      unixodbc unixodbc-dev \
  && rm -rf /var/lib/apt/lists/*

# ---------- (Optional) Microsoft ODBC Driver 18 ----------
# If you don't need SQL Server / pyodbc, you can skip this entire block
ARG INSTALL_MSODBCSQL18=1
RUN if [ "$INSTALL_MSODBCSQL18" = "1" ]; then \
      curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
      echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/microsoft-prod.list && \
      apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Safety net for libodbc soname (no-op if already present)
RUN test -e /usr/lib/x86_64-linux-gnu/libodbc.so.2 || \
    ln -s /usr/lib/x86_64-linux-gnu/libodbc.so /usr/lib/x86_64-linux-gnu/libodbc.so.2 || true

# ---------- Runtime ENV for your Django config ----------
# These match the vars your settings.py reads and what ffmpeg-based libs expect.
ENV FFMPEG_BIN=/usr/bin/ffmpeg \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    MEDIA_ROOT=/app/media \
    MEDIA_URL=/media/

# Prove ffmpeg exists at build time (good early failure if image changes)
RUN ffmpeg -hide_banner -version && which ffmpeg

# ---------- Python deps ----------
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# ---------- App code ----------
COPY . /app/

# ---------- Security: run as a non-root user ----------
RUN useradd -m appuser && \
    mkdir -p /app/media && chown -R appuser:appuser /app
USER appuser

# Expose the port your Gunicorn will bind to
EXPOSE 8003

# ---------- Entrypoint / CMD ----------
# - Ensure MEDIA_ROOT exists (idempotent)
# - Run migrations safely
# - Collect static into STATIC_ROOT (your settings point to /var/www/editorBackend/assets/)
#   If that path is mounted by your platform, make sure it’s writeable; otherwise you can
#   switch STATIC_ROOT to a project path or skip collectstatic in container and let nginx serve.
CMD bash -lc "\
  echo 'FFMPEG_BIN='${FFMPEG_BIN} && ffmpeg -hide_banner -version && \
  echo 'Ensuring MEDIA_ROOT at: '${MEDIA_ROOT} && mkdir -p \"${MEDIA_ROOT}\" && \
  python manage.py makemigrations --noinput || true && \
  python manage.py migrate --noinput && \
  # collectstatic is safe if STATIC_ROOT is writeable; comment out if nginx serves static directly
  (python manage.py collectstatic --noinput || true) && \
  python -m gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"
