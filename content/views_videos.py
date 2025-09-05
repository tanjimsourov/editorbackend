# content/views_videos.py
import pathlib, uuid, mimetypes, urllib.request
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from rest_framework import permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import VideoContent
from .serializers import VideoContentSerializer

def _unique_name(original: str) -> str:
    stem = get_valid_filename(pathlib.Path(original).stem) or "video"
    ext  = pathlib.Path(original).suffix or ".mp4"
    return f"{stem}-{uuid.uuid4().hex}{ext}"

def _is_video_mimetype(mt: str | None) -> bool:
    return bool(mt and mt.startswith("video/"))

class VideoUploadView(APIView):
    """
    POST /api/videos/upload
    multipart/form-data: file=<video>
    Returns: {"url": "/media/videos/<uid>/...mp4", ...serialized fields}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "file required (multipart field 'file')"}, status=400)

        mt = f.content_type or mimetypes.guess_type(f.name)[0]
        if not _is_video_mimetype(mt):
            return Response({"error": f"unsupported type: {mt or 'unknown'}"}, status=400)

        filename = _unique_name(f.name)
        asset = VideoContent(owner=request.user, name=f.name)
        asset.file.save(filename, f, save=True)

        ser = VideoContentSerializer(asset, context={"request": request})
        return Response({"url": asset.file.url, **ser.data}, status=201)

class VideoFetchView(APIView):
    """
    POST /api/videos/fetch
    JSON: {"url": "https://.../somevideo.mp4"}
    Server downloads and stores under /media/videos/<uid>/...
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
                if not _is_video_mimetype(mt):
                    return Response({"error": f"URL is not a video (content-type: {mt})"}, status=400)
                content = resp.read()
                suffix  = mimetypes.guess_extension(mt) or ".mp4"
        except Exception as e:
            return Response({"error": f"Download failed: {e}"}, status=400)

        original_name = pathlib.Path(parsed.path).name or f"remote{suffix}"
        filename = _unique_name(original_name)

        asset = VideoContent(owner=request.user, name=original_name)
        asset.file.save(filename, ContentFile(content), save=True)

        ser = VideoContentSerializer(asset, context={"request": request})
        return Response({"url": asset.file.url, **ser.data}, status=201)

class MyVideoListView(generics.ListAPIView):
    """
    GET /api/videos/list  — current user's videos
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoContentSerializer

    def get_queryset(self):
        return VideoContent.objects.filter(owner=self.request.user)

class MyVideoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/videos/<pk>/
    (Allow PATCH for name/duration_seconds if desired)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoContentSerializer

    def get_queryset(self):
        return VideoContent.objects.filter(owner=self.request.user)
