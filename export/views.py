# # export/views.py
# import os
# import shutil
# import subprocess
# from typing import Optional
#
# from django.conf import settings
# from django.utils.timezone import now
#
# from rest_framework.views import APIView
# from rest_framework.generics import GenericAPIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.parsers import MultiPartParser
# from rest_framework.permissions import IsAuthenticated
#
# from .models import LockedContent
#
# LOCKED_DIR = "locked"  # subfolder in MEDIA_ROOT
#
# # If True, when a non-MP4 upload is received and ffmpeg/transcode fails,
# # we keep the original WEBM and still return 200 with a warning.
# # If False, we return 500 on transcode failure.
# ALLOW_WEBM_FALLBACK = True
#
#
# # ---------- helpers ----------
#
# def _ensure_media_root() -> str:
#     media_root = getattr(settings, "MEDIA_ROOT", None)
#     if not media_root:
#         raise RuntimeError("MEDIA_ROOT is not configured")
#     os.makedirs(os.path.join(media_root, LOCKED_DIR), exist_ok=True)
#     return media_root
#
#
# def _rel_locked_path(filename: str) -> str:
#     return os.path.join(LOCKED_DIR, filename)
#
#
# def _abs_media_url(request, rel_path: str) -> str:
#     base = getattr(settings, "MEDIA_URL", "/media/")
#     if not base.endswith("/"):
#         base += "/"
#     # rel_path like "locked/41.mp4"
#     return request.build_absolute_uri(base + rel_path)
#
#
# def _ffmpeg_bin() -> Optional[str]:
#     """
#     Prefer settings.FFMPEG_BIN, then env FFMPEG_PATH, then 'ffmpeg' in PATH.
#     Return None if not found.
#     """
#     cand = getattr(settings, "FFMPEG_BIN", None) or os.environ.get("FFMPEG_PATH") or "ffmpeg"
#     if os.path.isabs(cand):
#         return cand if os.path.exists(cand) else None
#     return cand if shutil.which(cand) else None
#
#
# # ---------- API ----------
#
# class LockedCreateView(APIView):
#     """
#     POST /api/locked/create
#     JSON: { "name": str | null, "type": "image"|"video", "duration_seconds": int }
#     """
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         data = request.data
#         typ = (data.get("type") or "").strip()
#         if typ not in ("image", "video"):
#             return Response({"error": "type must be 'image' or 'video'"}, status=400)
#
#         try:
#             duration = int(data.get("duration_seconds") or 0)
#         except Exception:
#             duration = 0
#
#         name = (data.get("name") or "").strip() or f"Untitled {now().strftime('%Y-%m-%d %H:%M:%S')}"
#
#         lc = LockedContent.objects.create(
#             user=request.user,
#             name=name,
#             type=typ,
#             duration_seconds=duration,
#             status="locked",
#         )
#         return Response({
#             "id": lc.id,
#             "name": lc.name,
#             "type": lc.type,
#             "duration_seconds": lc.duration_seconds,
#             "status": lc.status,
#             "created_at": lc.created_at,
#         }, status=201)
#
#
# class LockedListView(APIView):
#     """
#     GET /api/locked/list  -> only current user's items
#     """
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         qs = LockedContent.objects.filter(user=request.user).order_by("-created_at")
#         out = []
#         for it in qs:
#             rel = it.file.name if it.file else None
#             out.append({
#                 "id": it.id,
#                 "name": it.name,
#                 "type": it.type,
#                 "duration_seconds": it.duration_seconds,
#                 "status": it.status,
#                 "created_at": it.created_at,
#                 "file": it.file.name if it.file else None,
#                 "file_url": _abs_media_url(request, rel) if rel else None,
#             })
#         return Response(out, status=200)
#
#
# class LockedSaveImageView(GenericAPIView):
#     """
#     POST /api/locked/<int:locked_id>/save-image
#     multipart/form-data: file=<png or image>; we persist as .png
#     """
#     parser_classes = [MultiPartParser]
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, locked_id: int):
#         # Ownership + type
#         try:
#             lc = LockedContent.objects.get(pk=locked_id, user=request.user, type="image")
#         except LockedContent.DoesNotExist:
#             return Response({"error": "Locked image not found"}, status=404)
#
#         f = request.FILES.get("file")
#         if not f:
#             return Response({"error": "file required (multipart field name 'file')"}, status=400)
#
#         ctype = (getattr(f, "content_type", "") or "").lower()
#         if not (ctype.startswith("image/") or ctype in ("application/octet-stream", "")):
#             return Response({"error": f"unexpected content_type: {ctype}"}, status=400)
#
#         try:
#             media_root = _ensure_media_root()
#             rel_path = _rel_locked_path(f"{locked_id}.png")
#             abs_path = os.path.join(media_root, rel_path)
#
#             with open(abs_path, "wb") as out:
#                 for chunk in f.chunks():
#                     out.write(chunk)
#
#             lc.file.name = rel_path
#             lc.status = "saved"
#             lc.save(update_fields=["file", "status"])
#
#             return Response({"fileUrl": _abs_media_url(request, rel_path)}, status=200)
#         except Exception as e:
#             return Response({"error": f"Failed to save image: {e}"}, status=500)
#
#
# class LockedSaveVideoView(GenericAPIView):
#     """
#     POST /api/locked/<int:locked_id>/save-video
#     multipart/form-data: file=<WEBM or MP4 or other container>
#     Behavior:
#       1) Persist the ORIGINAL upload immediately to MEDIA_ROOT/locked/<id>.<ext> and update the model,
#          so DB never stays null when the request is valid.
#       2) If not MP4, attempt to transcode to MP4 with ffmpeg.
#          - On success: swap file to <id>.mp4 and delete original.
#          - On failure or missing ffmpeg:
#              * If ALLOW_WEBM_FALLBACK: keep original and return 200 with a 'warning'.
#              * Else: return 500.
#     """
#     parser_classes = [MultiPartParser]
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, locked_id: int):
#         # Ownership + type
#         try:
#             lc = LockedContent.objects.get(pk=locked_id, user=request.user, type="video")
#         except LockedContent.DoesNotExist:
#             return Response({"error": "Locked video not found"}, status=404)
#
#         f = request.FILES.get("file")
#         if not f:
#             return Response({"error": "file required (multipart field name 'file')"}, status=400)
#
#         ctype = (getattr(f, "content_type", "") or "").lower()
#         if not (ctype.startswith("video/") or ctype in ("application/octet-stream", "")):
#             return Response({"error": f"unexpected content_type: {ctype}"}, status=400)
#
#         try:
#             media_root = _ensure_media_root()
#             out_dir = os.path.join(media_root, LOCKED_DIR)
#             os.makedirs(out_dir, exist_ok=True)
#
#             # Decide incoming extension based on filename or content-type
#             incoming_name = getattr(f, "name", "") or ""
#             in_ext = os.path.splitext(incoming_name)[1].lower()
#             if in_ext not in (".mp4", ".webm", ".mov", ".mkv", ".avi"):
#                 if ctype == "video/mp4":
#                     in_ext = ".mp4"
#                 elif ctype == "video/webm" or not in_ext:
#                     in_ext = ".webm"
#                 else:
#                     # Default to webm when unsure
#                     in_ext = ".webm"
#
#             is_mp4 = (in_ext == ".mp4" or ctype == "video/mp4")
#
#             # 1) Persist ORIGINAL upload immediately
#             orig_rel = _rel_locked_path(f"{locked_id}{in_ext}")
#             orig_abs = os.path.join(media_root, orig_rel)
#
#             with open(orig_abs, "wb") as out:
#                 for chunk in f.chunks():
#                     out.write(chunk)
#
#             # Reflect original in the model so DB isn't null anymore
#             lc.file.name = orig_rel
#             lc.status = "saved"  # Using "saved" once the binary is persisted; change to "locked" if you prefer
#             lc.save(update_fields=["file", "status"])
#
#             # If it's already mp4, done
#             if is_mp4:
#                 return Response({"fileUrl": _abs_media_url(request, orig_rel)}, status=200)
#
#             # 2) Try to transcode to MP4
#             ffmpeg = _ffmpeg_bin()
#             if not ffmpeg:
#                 if ALLOW_WEBM_FALLBACK:
#                     return Response({
#                         "fileUrl": _abs_media_url(request, orig_rel),
#                         "warning": "ffmpeg not found; kept original file.",
#                     }, status=200)
#                 return Response({"error": "ffmpeg not found. Configure settings.FFMPEG_BIN or PATH."}, status=500)
#
#             mp4_rel = _rel_locked_path(f"{locked_id}.mp4")
#             mp4_abs = os.path.join(media_root, mp4_rel)
#
#             cmd = [
#                 ffmpeg, "-y",
#                 "-hide_banner", "-loglevel", "error",
#                 "-i", orig_abs,
#                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
#                 "-preset", "fast", "-crf", "22",
#                 "-c:a", "aac", "-b:a", "128k",
#                 "-movflags", "+faststart",
#                 mp4_abs,
#             ]
#             proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
#             if proc.returncode != 0:
#                 if ALLOW_WEBM_FALLBACK:
#                     return Response({
#                         "fileUrl": _abs_media_url(request, orig_rel),
#                         "warning": "Transcode failed; kept original file.",
#                         "ffmpeg": proc.stderr[:5000],
#                     }, status=200)
#                 return Response({"error": "Transcode failed", "ffmpeg": proc.stderr}, status=500)
#
#             # Swap model to MP4 and remove original
#             try:
#                 if os.path.exists(orig_abs) and orig_abs != mp4_abs:
#                     try:
#                         os.remove(orig_abs)
#                     except Exception:
#                         pass
#
#                 lc.file.name = mp4_rel
#                 lc.status = "saved"
#                 lc.save(update_fields=["file", "status"])
#             except Exception as e:
#                 # MP4 created but model update failed; still return mp4 URL for debugging
#                 return Response({
#                     "error": f"Saved MP4 but failed to update model: {e}",
#                     "fileUrl": _abs_media_url(request, mp4_rel)
#                 }, status=500)
#
#             return Response({"fileUrl": _abs_media_url(request, mp4_rel)}, status=200)
#
#         except subprocess.TimeoutExpired:
#             if ALLOW_WEBM_FALLBACK:
#                 # Keep original file (likely WEBM)
#                 return Response({
#                     "fileUrl": _abs_media_url(request, lc.file.name),
#                     "warning": "Transcode timed out; kept original file."
#                 }, status=200)
#             return Response({"error": "Transcode timed out"}, status=500)
#         except Exception as e:
#             return Response({"error": f"Failed to save video: {e}"}, status=500)
