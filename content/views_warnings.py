# content/views_warnings.py
import pathlib, uuid, mimetypes, urllib.request
from urllib.parse import urlparse
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from PIL import Image as PILImage

from rest_framework import permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import WarningContent
from .serializers import WarningContentSerializer


def _unique_name(original: str, suffix: str = "") -> str:
    stem = get_valid_filename(pathlib.Path(original).stem) or "warning"
    ext = pathlib.Path(original).suffix or ".png"
    return f"{stem}{('-' + suffix) if suffix else ''}-{uuid.uuid4().hex}{ext}"


def _probe_dims_from_bytes(buf: bytes):
    try:
        with PILImage.open(BytesIO(buf)) as im:
            return im.width, im.height
    except Exception:
        return None, None


class WarningUploadView(APIView):
    """
    POST /api/warnings/upload/
    form-data: file=<image/*>, name?=..., category?=...
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "file required (multipart field 'file')"}, status=400)

        content_type = f.content_type or mimetypes.guess_type(getattr(f, "name", ""))[0]
        if not (content_type and content_type.startswith("image/")):
            return Response({"error": f"unsupported type: {content_type or 'unknown'}"}, status=400)

        in_name = getattr(f, "name", "warning.png")
        filename = _unique_name(in_name)
        name = request.data.get("name") or in_name
        category = request.data.get("category", "")

        item = WarningContent(owner=request.user, name=name, category=category)
        item.file.save(filename, f, save=True)

        # width/height
        try:
            with item.file.open("rb") as fp:
                buf = fp.read()
            w, h = _probe_dims_from_bytes(buf)
            if w and h:
                item.width = w
                item.height = h
                item.save(update_fields=["width", "height"])
        except Exception:
            pass

        ser = WarningContentSerializer(item, context={"request": request})
        return Response(ser.data, status=201)


class WarningFetchView(APIView):
    """
    POST /api/warnings/fetch/
    JSON: { "url": "https://...", "name"?: "...", "category"?: "..." }
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
                if not (mt and mt.startswith("image/")):
                    return Response({"error": f"URL is not an image (content-type: {mt})"}, status=400)
                buf = resp.read()
        except Exception as e:
            return Response({"error": f"Download failed: {e}"}, status=400)

        name = request.data.get("name") or pathlib.Path(parsed.path).name or "remote.png"
        category = request.data.get("category", "")
        filename = _unique_name(name, "fetched")

        item = WarningContent(owner=request.user, name=name, category=category)
        item.file.save(filename, ContentFile(buf), save=True)

        w, h = _probe_dims_from_bytes(buf)
        if w and h:
            item.width = w
            item.height = h
            item.save(update_fields=["width", "height"])

        ser = WarningContentSerializer(item, context={"request": request})
        return Response(ser.data, status=201)


class MyWarningListView(generics.ListAPIView):
    """
    GET /api/warnings/list/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WarningContentSerializer

    def get_queryset(self):
        qs = WarningContent.objects.filter(owner=self.request.user)
        # Optional: filter by category ?category=Fire
        cat = self.request.query_params.get("category")
        return qs.filter(category=cat) if cat else qs


class MyWarningDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/warnings/<pk>/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WarningContentSerializer

    def get_queryset(self):
        return WarningContent.objects.filter(owner=self.request.user)
