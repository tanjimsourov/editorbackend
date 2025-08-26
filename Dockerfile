# Dockerfile
FROM python:3.12

# Basics
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# ---- System deps ----
# unixODBC (+dev) for pyodbc, ffmpeg for imageio_ffmpeg, poppler-utils for pdf2image,
# curl/gnupg/ca-certs to add Microsoft's repo for msodbcsql18
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    unixodbc unixodbc-dev \
    ffmpeg \
    poppler-utils \
    curl gnupg ca-certificates apt-transport-https \
 && rm -rf /var/lib/apt/lists/*

# ---- Microsoft ODBC Driver 18 for SQL Server (Debian 12/bookworm base) ----
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

# (Safety net) ensure libodbc.so.2 is resolvable
RUN test -e /usr/lib/x86_64-linux-gnu/libodbc.so.2 || \
    ln -s /usr/lib/x86_64-linux-gnu/libodbc.so /usr/lib/x86_64-linux-gnu/libodbc.so.2 || true

# ---- Python deps ----
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install --no-cache-dir gunicorn  # ensure gunicorn is present even if not in requirements.txt

# ---- App code ----
COPY . /app/

# Ensure paths your settings expect exist
RUN mkdir -p /var/www/editorBackend/assets/ /app/media

# Expose your app port
EXPOSE 8003

# ---- Runtime: migrate + collectstatic + start gunicorn ----
CMD bash -lc "\
  python manage.py migrate --noinput && \
  python manage.py collectstatic --noinput && \
  python -m gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"