import os
import uuid
import subprocess
import shutil
from urllib.parse import urlparse, unquote

from django.conf import settings
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializers import TimelineSerializer
from .models import LockedContent
from .ffmpegkit.builder import build_ffmpeg_cmd, build_ffmpeg_cmd_still  # <- NEW import

try:
    import requests
except ImportError:
    requests = None


# ---- shared helpers (unchanged, trimmed to what we need) ----

def _normalize_src_to_abs_url(request, src: str) -> str:
    p = urlparse(src)
    if p.scheme in ("http", "https", "data", "blob"):
        return src
    if src.startswith("/"):
        return request.build_absolute_uri(src)
    return request.build_absolute_uri("/" + src)


def _strip_leading_slashes(path_or_url: str) -> str:
    return unquote(path_or_url.lstrip("/"))


def _map_media_static_to_fs(path_part: str) -> str | None:
    media_url = getattr(settings, "MEDIA_URL", "") or ""
    static_url = getattr(settings, "STATIC_URL", "") or ""
    m_prefix = media_url if media_url.endswith("/") else media_url + "/"
    s_prefix = static_url if static_url.endswith("/") else static_url + "/"

    if m_prefix and path_part.startswith(m_prefix.lstrip("/")):
        rel = path_part[len(m_prefix.lstrip("/")):]
        candidate = os.path.join(str(settings.MEDIA_ROOT), rel)
        if os.path.isfile(candidate):
            return candidate

    if s_prefix and path_part.startswith(s_prefix.lstrip("/")):
        rel = path_part[len(s_prefix.lstrip("/")):]
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            candidate = os.path.join(str(static_root), rel)
            if os.path.isfile(candidate):
                return candidate
    return None


def _try_map_to_local_file(src_or_url: str) -> str | None:
    p = urlparse(src_or_url)
    if p.scheme in ("http", "https"):
        path_part = _strip_leading_slashes(p.path)
        hit = _map_media_static_to_fs(path_part)
        if hit:
            return hit
        rel_path = path_part
    else:
        if src_or_url.startswith("/"):
            hit = _map_media_static_to_fs(_strip_leading_slashes(src_or_url))
            if hit:
                return hit
        rel_path = _strip_leading_slashes(src_or_url)

    if not rel_path:
        return None

    candidates_rel = [rel_path]
    if rel_path.startswith("videos/"):
        candidates_rel.append(rel_path[len("videos/"):])

    for base in getattr(settings, "ASSET_FALLBACK_DIRS", []):
        for rel in candidates_rel:
            candidate = os.path.join(str(base), rel)
            if os.path.isfile(candidate):
                return candidate

    videos_root = getattr(settings, "VIDEOS_ROOT", None)
    if videos_root:
        for rel in candidates_rel:
            candidate = os.path.join(str(videos_root), rel)
            if os.path.isfile(candidate):
                return candidate
    return None


_ASSET_CACHE: dict[str, str] = {}


def _download_once_to_tmp(abs_url: str) -> str:
    if abs_url in _ASSET_CACHE:
        return _ASSET_CACHE[abs_url]
    if requests is None:
        raise RuntimeError("The 'requests' package is required to download remote assets.")

    import tempfile
    parsed = urlparse(abs_url)
    fname = os.path.basename(parsed.path) or "asset"
    root, ext = os.path.splitext(fname)
    fd, tmp_path = tempfile.mkstemp(prefix="render_asset_", suffix=ext or "")
    os.close(fd)

    try:
        with requests.get(abs_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

    _ASSET_CACHE[abs_url] = tmp_path
    return tmp_path


def _to_local_path(request, src_or_url: str) -> str:
    local = _try_map_to_local_file(src_or_url)
    if local and os.path.exists(local):
        return local

    p = urlparse(src_or_url)
    if p.scheme in ("http", "https"):
        abs_url = src_or_url if p.netloc else _normalize_src_to_abs_url(request, src_or_url)
        return _download_once_to_tmp(abs_url)

    if src_or_url.startswith("/"):
        abs_url = _normalize_src_to_abs_url(request, src_or_url)
        return _download_once_to_tmp(abs_url)

    return src_or_url


def _localize_timeline_assets(request, timeline: dict) -> dict:
    tl = dict(timeline)
    if tl.get("backgroundImage"):
        tl["backgroundImage"] = _to_local_path(request, tl["backgroundImage"])

    new_tracks = []
    for tr in tl.get("tracks", []):
        tr2 = dict(tr)
        ttype = tr2.get("type")
        if ttype in ("video", "image", "audio"):
            src = tr2.get("src")
            if src:
                tr2["src"] = _to_local_path(request, src)
        new_tracks.append(tr2)
    tl["tracks"] = new_tracks
    return tl


def _ensure_dir_inside_media(subdir: str) -> str:
    root = getattr(settings, "MEDIA_ROOT", None)
    if not root:
        raise RuntimeError("MEDIA_ROOT is not configured")
    abs_dir = os.path.join(root, subdir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def _media_url_for(request, rel_path: str) -> str:
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    if not media_url.endswith("/"):
        media_url += "/"
    return request.build_absolute_uri(media_url + rel_path)


def _resolve_ffmpeg_bin() -> str | None:
    ff = getattr(settings, "FFMPEG_BIN", None)
    if ff:
        ff = os.path.expandvars(os.path.expanduser(str(ff)))
        if os.path.isfile(ff):
            return ff
        found = shutil.which(ff)
        if found:
            return found
    return shutil.which("ffmpeg")


# --------------------------- VIDEO endpoints (unchanged) ---------------------------

class PreviewRenderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TimelineSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data

        # localize
        try:
            data_local = _localize_timeline_assets(request, data)
        except Exception as e:
            return Response({"error": f"Failed to localize assets: {e}"}, status=400)

        rid = uuid.uuid4().hex
        out_dir = _ensure_dir_inside_media("previews")
        filename = f"{rid}.mp4"
        output_path = os.path.join(out_dir, filename)

        try:
            args = build_ffmpeg_cmd(data_local, output_path)
        except Exception as e:
            return Response({"error": f"Failed to build ffmpeg graph: {e}"}, status=400)

        ffmpeg_bin = _resolve_ffmpeg_bin()
        if not ffmpeg_bin:
            return Response({"error": "ffmpeg not found. Configure FFMPEG_BIN or PATH."}, status=400)

        try:
            subprocess.run([ffmpeg_bin, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            return Response({"error": "ffmpeg failed", "stderr": e.stderr.decode("utf-8", errors="ignore")}, status=500)

        rel_path = f"previews/{filename}"
        return Response({"preview_url": _media_url_for(request, rel_path), "render_id": rid}, status=200)


class RenderSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TimelineSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        name = (data.get("name") or "").strip() or f"Untitled {now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            data_local = _localize_timeline_assets(request, data)
        except Exception as e:
            return Response({"error": f"Failed to localize assets: {e}"}, status=400)

        # Always treat this endpoint as VIDEO (as requested)
        try:
            duration = float(data.get("duration") or 0.0)
        except Exception:
            duration = 0.0

        lc = LockedContent.objects.create(
            user=request.user,
            name=name,
            type="video",
            duration_seconds=int(max(1, round(duration))),
            status="locked",
        )

        out_dir = _ensure_dir_inside_media("locked")
        output_rel = f"locked/{lc.id}.mp4"
        output_abs = os.path.join(out_dir, f"{lc.id}.mp4")

        ffmpeg_bin = _resolve_ffmpeg_bin()
        if not ffmpeg_bin:
            lc.delete()
            return Response({"error": "ffmpeg not found. Configure FFMPEG_BIN or PATH."}, status=400)

        try:
            args = build_ffmpeg_cmd(data_local, output_abs)
        except Exception as e:
            lc.delete()
            return Response({"error": f"Failed to build ffmpeg graph: {e}"}, status=400)

        try:
            subprocess.run([ffmpeg_bin, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            lc.delete()
            return Response({"error": "ffmpeg failed", "stderr": e.stderr.decode("utf-8", errors="ignore")}, status=500)

        lc.file.name = output_rel
        lc.status = "saved"
        lc.save(update_fields=["file", "status"])

        return Response({
            "id": lc.id,
            "name": lc.name,
            "type": lc.type,
            "duration_seconds": lc.duration_seconds,
            "status": lc.status,
            "created_at": lc.created_at,
            "file": lc.file.name,
            "file_url": _media_url_for(request, output_rel),
        }, status=200)


# --------------------------- NEW: IMAGE endpoints (use ffmpeg STILL) ---------------------------

class ImagePreviewView(APIView):
    """
    POST /api/render/image/preview
    Renders one frame (PNG) from the full graph.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TimelineSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data

        try:
            data_local = _localize_timeline_assets(request, data)
        except Exception as e:
            return Response({"error": f"Failed to localize assets: {e}"}, status=400)

        rid = uuid.uuid4().hex
        out_dir = _ensure_dir_inside_media("previews")
        filename = f"{rid}.png"
        output_path = os.path.join(out_dir, filename)

        try:
            args = build_ffmpeg_cmd_still(data_local, output_path, fmt="png")
        except Exception as e:
            return Response({"error": f"Failed to build still graph: {e}"}, status=400)

        ffmpeg_bin = _resolve_ffmpeg_bin()
        if not ffmpeg_bin:
            return Response({"error": "ffmpeg not found. Configure FFMPEG_BIN or PATH."}, status=400)

        try:
            subprocess.run([ffmpeg_bin, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            return Response({"error": "ffmpeg failed", "stderr": e.stderr.decode("utf-8", errors="ignore")}, status=500)

        rel_path = f"previews/{filename}"
        return Response({"preview_url": _media_url_for(request, rel_path), "render_id": rid}, status=200)


class ImageSaveView(APIView):
    """
    POST /api/render/image
    Saves one PNG into LockedContent (type='image').
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TimelineSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data

        name = (data.get("name") or "").strip() or f"Untitled {now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            data_local = _localize_timeline_assets(request, data)
        except Exception as e:
            return Response({"error": f"Failed to localize assets: {e}"}, status=400)

        lc = LockedContent.objects.create(
            user=request.user,
            name=name,
            type="image",
            duration_seconds=0,
            status="locked",
        )

        out_dir = _ensure_dir_inside_media("locked")
        output_rel = f"locked/{lc.id}.png"
        output_abs = os.path.join(out_dir, f"{lc.id}.png")

        ffmpeg_bin = _resolve_ffmpeg_bin()
        if not ffmpeg_bin:
            lc.delete()
            return Response({"error": "ffmpeg not found. Configure FFMPEG_BIN or PATH."}, status=400)

        try:
            args = build_ffmpeg_cmd_still(data_local, output_abs, fmt="png")
        except Exception as e:
            lc.delete()
            return Response({"error": f"Failed to build still graph: {e}"}, status=400)

        try:
            subprocess.run([ffmpeg_bin, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            lc.delete()
            return Response({"error": "ffmpeg failed", "stderr": e.stderr.decode("utf-8", errors="ignore")}, status=500)

        lc.file.name = output_rel
        lc.status = "saved"
        lc.save(update_fields=["file", "status"])

        return Response({
            "id": lc.id,
            "name": lc.name,
            "type": lc.type,
            "duration_seconds": lc.duration_seconds,
            "status": lc.status,
            "created_at": lc.created_at,
            "file": lc.file.name,
            "file_url": _media_url_for(request, output_rel),
        }, status=200)


class LockedListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LockedContent.objects.filter(user=request.user).order_by("-created_at")
        out = []
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if not media_url.endswith("/"):
            media_url += "/"

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
                "file_url": (request.build_absolute_uri(media_url + rel) if rel else None),
            })
        return Response(out, status=200)
