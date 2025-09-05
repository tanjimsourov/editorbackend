# content/views_images.py
import pathlib, uuid, mimetypes, urllib.request
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from PIL import Image as PILImage  # Pillow to read width/height (optional)
from io import BytesIO

from rest_framework import permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ImageContent
from .serializers import ImageContentSerializer

def _unique_name(original: str) -> str:
    stem = get_valid_filename(pathlib.Path(original).stem) or "image"
    ext = pathlib.Path(original).suffix or ".png"
    return f"{stem}-{uuid.uuid4().hex}{ext}"

def _is_image_mimetype(mt: str | None) -> bool:
    return bool(mt and mt.startswith("image/"))

def _probe_dims(fp) -> tuple[int | None, int | None]:
    try:
        with PILImage.open(fp) as im:
            return im.width, im.height
    except Exception:
        return None, None

class ImageUploadView(APIView):
    """
    POST /api/images/upload/
    multipart/form-data: file=<image/*>
    Returns: {"url": "/media/images/<uid>/...", "id", "name", "file_url", "width", "height", "created_at"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "file required (multipart field 'file')"}, status=400)

        mt = f.content_type or mimetypes.guess_type(getattr(f, "name", ""))[0]
        if not _is_image_mimetype(mt):
            return Response({"error": f"unsupported type: {mt or 'unknown'}"}, status=400)

        filename = _unique_name(getattr(f, "name", "image.png"))
        item = ImageContent(owner=request.user, name=getattr(f, "name", filename))

        # Save, then fill width/height
        item.file.save(filename, f, save=True)

        # Try to read dimensions (use a fresh read from storage)
        try:
            with item.file.open("rb") as fp:
                w, h = _probe_dims(fp)
                if w and h:
                    item.width = w
                    item.height = h
                    item.save(update_fields=["width", "height"])
        except Exception:
            pass

        ser = ImageContentSerializer(item, context={"request": request})
        return Response(ser.data, status=201)

class ImageFetchView(APIView):
    """
    POST /api/images/fetch/
    JSON: {"url": "https://.../image.png"}
    Server downloads and stores under /media/images/<uid>/...
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        remote = (request.data or {}).get("url")
        if not remote:
            return Response({"error": "Missing url"}, status=400)

        parsed = urlparse(remote)
        if parsed.scheme not in ("http", "https"):
            return Response({"error": "Only http/https URLs allowed"}, status=400)

        try:
            with urllib.request.urlopen(remote, timeout=25) as resp:
                mt = resp.headers.get_content_type()
                if not _is_image_mimetype(mt):
                    return Response({"error": f"URL is not an image (content-type: {mt})"}, status=400)
                content = resp.read()
                suffix = mimetypes.guess_extension(mt) or ".png"
        except Exception as e:
            return Response({"error": f"Download failed: {e}"}, status=400)

        original_name = pathlib.Path(parsed.path).name or f"remote{suffix}"
        filename = _unique_name(original_name)

        item = ImageContent(owner=request.user, name=original_name)
        item.file.save(filename, ContentFile(content), save=True)

        # Probe width/height from downloaded bytes
        try:
          with BytesIO(content) as fp:
              w, h = _probe_dims(fp)
              if w and h:
                  item.width = w
                  item.height = h
                  item.save(update_fields=["width", "height"])
        except Exception:
          pass

        ser = ImageContentSerializer(item, context={"request": request})
        return Response(ser.data, status=201)

class MyImageListView(generics.ListAPIView):
    """
    GET /api/images/list/
    Current user's images
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ImageContentSerializer

    def get_queryset(self):
        return ImageContent.objects.filter(owner=self.request.user)

class MyImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/images/<pk>/
    Allow PATCH for name/width/height if needed
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ImageContentSerializer

    def get_queryset(self):
        return ImageContent.objects.filter(owner=self.request.user)
