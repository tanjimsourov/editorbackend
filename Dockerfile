# Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Put Playwright browsers in a fixed, shared path (not per-user cache)
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# ---------- System deps ----------
# ffmpeg: video trim/encode
# fonts: drawtext & emoji; include Debian names for Ubuntu-equivalents
# chromium deps: runtime libs needed by Playwright's Chromium
# poppler-utils: optional (PDF raster)
# curl/gnupg/ca-certs: for optional MS ODBC repo
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ffmpeg \
      fontconfig fonts-dejavu fonts-unifont fonts-ubuntu \
      poppler-utils \
      curl gnupg ca-certificates apt-transport-https \
      unixodbc unixodbc-dev \
      # ---- Chromium runtime libs ----
      libnss3 libxss1 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libnspr4 libxcb1 libxcomposite1 libxdamage1 libxfixes3 \
      libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
      libgtk-3-0 \
  && rm -rf /var/lib/apt/lists/*

# ---------- (Optional) Microsoft ODBC Driver 18 ----------
# If you don't need SQL Server / pyodbc, set --build-arg INSTALL_MSODBCSQL18=0
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

# ---------- Runtime ENV ----------
ENV FFMPEG_BIN=/usr/bin/ffmpeg \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    MEDIA_ROOT=/app/media \
    MEDIA_URL=/media/

# Prove ffmpeg exists at build time
RUN ffmpeg -hide_banner -version && which ffmpeg

# ---------- Python deps ----------
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Ensure Playwright (Python) is installed even if not in requirements.txt
    pip install --no-cache-dir playwright==1.47.0 && \
    pip install --no-cache-dir gunicorn

# ---------- Download Playwright browsers at build time ----------
# IMPORTANT: drop "--with-deps" (it uses an Ubuntu script that breaks on Debian).
RUN python -m playwright install chromium

# ---------- App code ----------
COPY . /app/

# ---------- Non-root user & permissions ----------
RUN useradd -m appuser && \
    mkdir -p /app/media /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright
USER appuser

EXPOSE 8003

# ---------- CMD (JSON form) ----------
CMD ["bash","-lc","\
  echo 'FFMPEG_BIN='${FFMPEG_BIN} && ffmpeg -hide_banner -version && \
  echo 'Ensuring MEDIA_ROOT at: '${MEDIA_ROOT} && mkdir -p \"${MEDIA_ROOT}\" && \
  python manage.py makemigrations --noinput || true && \
  python manage.py migrate --noinput && \
  (python manage.py collectstatic --noinput || true) && \
  gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"]
