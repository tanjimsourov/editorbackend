# Use an official Python runtime as the base image
FROM python:3.12

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Workdir
WORKDIR /app

# ---- System dependencies ----
# - build-essential: compile wheels if needed
# - unixODBC + unixODBC-dev: required by pyodbc
# - ffmpeg: required by imageio_ffmpeg in your settings
# - curl/gnupg/ca-certs/apt-transport-https: to add Microsoft repo for msodbcsql18
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    unixodbc unixodbc-dev \
    ffmpeg \
    curl gnupg ca-certificates apt-transport-https \
  && rm -rf /var/lib/apt/lists/*

# ---- Microsoft ODBC Driver 18 for SQL Server ----
# (Python image is Debian 12/bookworm)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
  && apt-get update \
  && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
  && rm -rf /var/lib/apt/lists/*

# ---- Python deps ----
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
  && pip install -r requirements.txt

# ---- App code ----
COPY . /app/

# Ensure paths your settings expect exist
# (STATIC_ROOT default in your settings points to /var/www/editorBackend/assets/)
RUN mkdir -p /var/www/editorBackend/assets/ /app/media

# Expose the port your app will bind to (keep 8003 as you provided)
EXPOSE 8003

# ---- Runtime: migrate + collectstatic + start gunicorn ----
# Doing these at runtime ensures static ends up on any attached volume and
# avoids DB/driver dependencies during the build stage.
CMD bash -lc "\
  python manage.py migrate --noinput && \
  python manage.py collectstatic --noinput && \
  gunicorn editorBackend.wsgi:application --bind 0.0.0.0:8003 --workers 3 --timeout 120 \
"
