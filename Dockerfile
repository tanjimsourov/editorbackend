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

# --- Microsoft ODBC Driver 18 (if you need pyodbc) ---
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

# Safety net for libodbc soname
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

# Ensure media path exists (and mount as a volume in Coolify for persistence)
RUN mkdir -p /app/media

EXPOSE 8003

# --- Runtime: migrate + start gunicorn (collectstatic removed) ---
CMD bash -lc "\
  echo 'FFMPEG_BIN='$FFMPEG_BIN && ffmpeg -hide_banner -version && \
  python manage.py migrate --noinput && \
  python -m gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"
