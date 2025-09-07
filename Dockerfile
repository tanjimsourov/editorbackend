# Dockerfile
# Use Debian 12 (bookworm) so Microsoft ODBC Driver 18 packages install cleanly.
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Store Playwright browsers in a fixed, image-level path
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    # App media defaults (match your settings.py)
    FFMPEG_BIN=/usr/bin/ffmpeg \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    MEDIA_ROOT=/app/media \
    MEDIA_URL=/media/

WORKDIR /app

# ---------- System deps (Debian bookworm) ----------
# - ffmpeg for trims/encodes
# - fonts: Noto + Unifont (broad script + emoji)
# - Chromium runtime libs for Playwright
# - poppler-utils optional (PDF raster)
# - unixODBC + dev headers for pyodbc
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ffmpeg \
      fontconfig fonts-dejavu fonts-unifont \
      fonts-noto-core fonts-noto-extra fonts-noto-color-emoji \
      poppler-utils \
      curl gnupg ca-certificates apt-transport-https \
      unixodbc unixodbc-dev \
      libnss3 libxss1 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libnspr4 libxcb1 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
      libgtk-3-0 \
  && rm -rf /var/lib/apt/lists/*

# ---------- Microsoft ODBC Driver 18 for SQL Server ----------
# Official MS repo for Debian 12 (bookworm)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/microsoft-prod.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*

# Safety net for libodbc soname (usually not needed, harmless if present)
RUN test -e /usr/lib/x86_64-linux-gnu/libodbc.so.2 || \
    ln -s /usr/lib/x86_64-linux-gnu/libodbc.so /usr/lib/x86_64-linux-gnu/libodbc.so.2 || true

# Prove ffmpeg exists at build time (early fail if base changes)
RUN ffmpeg -hide_banner -version && which ffmpeg

# ---------- Python deps ----------
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Ensure Playwright (Python) + gunicorn present even if not pinned in requirements
    pip install --no-cache-dir playwright==1.47.0 gunicorn

# ---------- Bake Playwright browsers (Chromium) ----------
# IMPORTANT: do NOT use --with-deps (Ubuntu-only installer scripts).
RUN python -m playwright install chromium

# ---------- App code ----------
COPY . /app/

# ---------- Non-root user & permissions ----------
RUN useradd -m appuser && \
    mkdir -p /app/media /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright
USER appuser

EXPOSE 8003

# ---------- CMD (JSON form; resilient startup) ----------
# - makemigrations: best-effort (won't crash container if DB temporarily unavailable)
# - migrate: best-effort as well; logs warning if it fails so app can still boot
CMD ["bash","-lc","\
  echo 'FFMPEG_BIN='${FFMPEG_BIN} && ffmpeg -hide_banner -version && \
  echo 'Ensuring MEDIA_ROOT at: '${MEDIA_ROOT} && mkdir -p \"${MEDIA_ROOT}\" && \
  (python manage.py makemigrations --noinput || echo '[WARN] makemigrations failed (continuing)') && \
  (python manage.py migrate --noinput || echo '[WARN] migrate failed (continuing)') && \
  (python manage.py collectstatic --noinput || echo '[WARN] collectstatic failed (continuing)') && \
  gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"]
