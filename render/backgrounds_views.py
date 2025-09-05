import os
import uuid
import imghdr
import mimetypes
import requests
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, parsers


def _ext_from_bytes(b: bytes, fallback: str = ".jpg") -> str:
    kind = imghdr.what(None, h=b)
    if kind == "jpeg":
        return ".jpg"
    if kind:
        return f".{kind}"
    return fallback


def _save_bytes_to_media(data: bytes, subdir: str = "backgrounds", filename: str | None = None) -> str:
    os.makedirs(os.path.join(settings.MEDIA_ROOT, subdir), exist_ok=True)
    ext = _ext_from_bytes(data)
    name = filename or (str(uuid.uuid4()) + ext)
    path = os.path.join(subdir, name)
    default_storage.save(path, ContentFile(data))
    return settings.MEDIA_URL.rstrip("/") + "/" + path.replace("\\", "/")


class BackgroundUploadView(APIView):
    """
    POST multipart/form-data with a file field named 'file'
    -> { url: '/media/backgrounds/uuid.jpg' }
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "Missing file."}, status=400)
        data = f.read()
        url = _save_bytes_to_media(data, subdir="backgrounds")
        return Response({"url": url}, status=201)


class BackgroundFetchView(APIView):
    """
    POST JSON { "url": "<remote image url>" }
    Server downloads and stores -> { url: '/media/backgrounds/uuid.jpg' }
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        remote_url = (request.data or {}).get("url")
        if not remote_url:
            return Response({"error": "Missing url."}, status=400)

        try:
            # Stream download into memory (small images are fine)
            r = requests.get(remote_url, timeout=15)
            if r.status_code != 200:
                return Response({"error": f"Fetch failed: HTTP {r.status_code}"}, status=400)
            data = r.content
            if not data or len(data) < 10:
                return Response({"error": "Empty image content."}, status=400)
        except Exception as e:
            return Response({"error": f"Failed to fetch: {e}"}, status=400)

        # Optional content-type check
        ctype = r.headers.get("Content-Type", "")
        if "image" not in ctype.lower():
            # try a sniff; still accept if it's a known image
            if not imghdr.what(None, h=data):
                return Response({"error": f"Not an image (content-type: {ctype})"}, status=400)

        # Use last path part for nicer filenames
        parsed = urlparse(remote_url)
        base_name = os.path.basename(parsed.path) or f"{uuid.uuid4()}.jpg"
        url = _save_bytes_to_media(data, subdir="backgrounds", filename=base_name)
        return Response({"url": url}, status=201)
