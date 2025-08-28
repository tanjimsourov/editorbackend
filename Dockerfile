# Dockerfile
FROM python:3.12

# Basics
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# --- System deps (includes ffmpeg) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    unixodbc unixodbc-dev \
    ffmpeg \
    poppler-utils \
    curl gnupg ca-certificates apt-transport-https \
 && rm -rf /var/lib/apt/lists/*

# --- Microsoft ODBC Driver 18 (optional; needed if you use pyodbc) ---
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

# Safety net for libodbc soname (no-op if already present)
RUN test -e /usr/lib/x86_64-linux-gnu/libodbc.so.2 || \
    ln -s /usr/lib/x86_64-linux-gnu/libodbc.so /usr/lib/x86_64-linux-gnu/libodbc.so.2 || true

# Pin ffmpeg path for app + libs
ENV FFMPEG_BIN=/usr/bin/ffmpeg \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
    MEDIA_ROOT=/app/media \
    MEDIA_URL=/media/

# Prove ffmpeg exists at build
RUN ffmpeg -hide_banner -version && which ffmpeg

# Python deps
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install --no-cache-dir gunicorn

# App code
COPY . /app/

# Do NOT create media at build time; Coolify should mount a persistent volume here.
# (If volume is mounted, it will overlay /app/media without deleting existing data.)

EXPOSE 8003

# --- Runtime: ensure media dir exists (non-destructive), then makemigrations + migrate, then start gunicorn ---
# Notes:
# - `mkdir -p "$MEDIA_ROOT"` is idempotent and will NOT remove/overwrite existing media.
# - `makemigrations` is safe even if no changes; it will simply do nothing.
# - If you commit migration files to git, you may skip makemigrations here.
CMD bash -lc "\
  echo 'FFMPEG_BIN='$FFMPEG_BIN && ffmpeg -hide_banner -version && \
  echo 'Ensuring MEDIA_ROOT exists at: '$MEDIA_ROOT && mkdir -p \"$MEDIA_ROOT\" && \
  python manage.py makemigrations --noinput || true && \
  python manage.py migrate --noinput && \
  python -m gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"
