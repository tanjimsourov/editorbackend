# export/views.py
import os
import shutil
import subprocess

from django.conf import settings
from django.utils.timezone import now
from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import LockedContent

LOCKED_DIR = "locked"  # subfolder in MEDIA_ROOT


# ---------- helpers ----------

def _ensure_media_root() -> str:
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        raise RuntimeError("MEDIA_ROOT is not configured")
    os.makedirs(os.path.join(media_root, LOCKED_DIR), exist_ok=True)
    return media_root


def _rel_locked_path(filename: str) -> str:
    return os.path.join(LOCKED_DIR, filename)


def _abs_media_url(request, rel_path: str) -> str:
    base = settings.MEDIA_URL or "/media/"
    if not base.endswith("/"):
        base += "/"
    return request.build_absolute_uri(base + rel_path)


def _ffmpeg_bin() -> str | None:
    # Prefer settings.FFMPEG_BIN, then env FFMPEG_PATH, then "ffmpeg" in PATH
    cand = getattr(settings, "FFMPEG_BIN", None) or os.environ.get("FFMPEG_PATH") or "ffmpeg"
    if os.path.isabs(cand):
        return cand if os.path.exists(cand) else None
    return cand if shutil.which(cand) else None


# ---------- API ----------

class LockedCreateView(APIView):
    """
    POST /api/locked/create
    JSON: { "name": str | null, "type": "image"|"video", "duration_seconds": int }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        typ = (data.get("type") or "").strip()
        if typ not in ("image", "video"):
            return Response({"error": "type must be 'image' or 'video'"}, status=400)

        try:
            duration = int(data.get("duration_seconds") or 0)
        except Exception:
            duration = 0

        name = (data.get("name") or "").strip() or f"Untitled {now().strftime('%Y-%m-%d %H:%M:%S')}"

        lc = LockedContent.objects.create(
            user=request.user,
            name=name,
            type=typ,
            duration_seconds=duration,
            status="locked",
        )
        return Response({
            "id": lc.id,  # int (AutoField)
            "name": lc.name,
            "type": lc.type,
            "duration_seconds": lc.duration_seconds,
            "status": lc.status,
            "created_at": lc.created_at,
        }, status=201)


class LockedListView(APIView):
    """
    GET /api/locked/list  -> only current user's items
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LockedContent.objects.filter(user=request.user).order_by("-created_at")
        out = []
        for it in qs:
            rel = it.file.name if it.file else None
            out.append({
                "id": it.id,
                "name": it.name,
                "type": it.type,
                "duration_seconds": it.duration_seconds,
                "status": it.status,
                "created_at": it.created_at,
                "file": it.file.name if it.file else None,
                "file_url": _abs_media_url(request, rel) if rel else None,
            })
        return Response(out, status=200)


class LockedSaveImageView(GenericAPIView):
    """
    POST /api/locked/<int:locked_id>/save-image
    multipart/form-data: file=<png or image>; we persist as .png
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, locked_id: int):
        # Ownership + type
        try:
            lc = LockedContent.objects.get(pk=locked_id, user=request.user, type="image")
        except LockedContent.DoesNotExist:
            return Response({"error": "Locked image not found"}, status=404)

        f = request.FILES.get("file")
        if not f:
            return Response({"error": "file required (multipart field name 'file')"}, status=400)

        ctype = (getattr(f, "content_type", "") or "").lower()
        if not (ctype.startswith("image/") or ctype in ("application/octet-stream", "")):
            return Response({"error": f"unexpected content_type: {ctype}"}, status=400)

        try:
            media_root = _ensure_media_root()
            rel_path = _rel_locked_path(f"{locked_id}.png")
            abs_path = os.path.join(media_root, rel_path)

            with open(abs_path, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)

            lc.file.name = rel_path
            lc.status = "saved"
            lc.save(update_fields=["file", "status"])

            return Response({"fileUrl": _abs_media_url(request, rel_path)}, status=200)
        except Exception as e:
            return Response({"error": f"Failed to save image: {e}"}, status=500)


class LockedSaveVideoView(GenericAPIView):
    """
    POST /api/locked/<int:locked_id>/save-video
    multipart/form-data: file=<WEBM or MP4>
    - If not MP4, transcodes to MP4 using ffmpeg binary (settings.FFMPEG_BIN or PATH)
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, locked_id: int):
        # Ownership + type
        try:
            lc = LockedContent.objects.get(pk=locked_id, user=request.user, type="video")
        except LockedContent.DoesNotExist:
            return Response({"error": "Locked video not found"}, status=404)

        f = request.FILES.get("file")
        if not f:
            return Response({"error": "file required (multipart field name 'file')"}, status=400)

        ctype = (getattr(f, "content_type", "") or "").lower()
        if not (ctype.startswith("video/") or ctype in ("application/octet-stream", "")):
            return Response({"error": f"unexpected content_type: {ctype}"}, status=400)

        ffmpeg = _ffmpeg_bin()
        if not ffmpeg:
            return Response({"error": "ffmpeg not found. Configure settings.FFMPEG_BIN or PATH."}, status=500)

        try:
            media_root = _ensure_media_root()
            out_dir = os.path.join(media_root, LOCKED_DIR)
            os.makedirs(out_dir, exist_ok=True)

            uploaded_tmp = os.path.join(out_dir, f"{locked_id}.upload")
            with open(uploaded_tmp, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)

            incoming_name = getattr(f, "name", "") or ""
            is_mp4 = incoming_name.lower().endswith(".mp4") or ctype == "video/mp4"
            mp4_path = os.path.join(out_dir, f"{locked_id}.mp4")

            if is_mp4:
                # Trust the incoming MP4; move into place
                os.replace(uploaded_tmp, mp4_path)
            else:
                # Treat as WEBM/other; transcode to MP4
                webm_path = os.path.join(out_dir, f"{locked_id}.webm")
                os.replace(uploaded_tmp, webm_path)

                cmd = [
                    ffmpeg, "-y",
                    "-hide_banner", "-loglevel", "error",
                    "-i", webm_path,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "fast", "-crf", "22",
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    mp4_path,
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if proc.returncode != 0:
                    return Response({"error": "Transcode failed", "ffmpeg": proc.stderr}, status=500)
                try:
                    os.remove(webm_path)
                except Exception:
                    pass

            rel_path = _rel_locked_path(f"{locked_id}.mp4")
            lc.file.name = rel_path
            lc.status = "saved"
            lc.save(update_fields=["file", "status"])

            return Response({"fileUrl": _abs_media_url(request, rel_path)}, status=200)

        except subprocess.TimeoutExpired:
            return Response({"error": "Transcode timed out"}, status=500)
        except Exception as e:
            return Response({"error": f"Failed to save video: {e}"}, status=500)
