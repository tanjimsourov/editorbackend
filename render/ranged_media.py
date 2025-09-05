# render/ranged_media.py
import mimetypes, os
from django.conf import settings
from django.http import (
    FileResponse, HttpResponse, StreamingHttpResponse, HttpResponseNotFound
)
from django.utils.http import http_date
from django.utils._os import safe_join

def _add_cors_headers(resp):
    # Public media: allow any origin. If you prefer, restrict to your frontend origin(s).
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Access-Control-Expose-Headers"] = "Content-Length, Content-Range, Accept-Ranges"
    resp["Accept-Ranges"] = "bytes"
    return resp

def _open_file_range(path, start: int, end: int, block_size: int = 8192):
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(block_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk

def serve_media(request, path: str):
    """
    Minimal, range-aware media server for MP4/PNG/etc.
    Use Nginx/S3 for production if possible; this unblocks playback immediately.
    """
    try:
        fullpath = safe_join(str(settings.MEDIA_ROOT), path)
    except Exception:
        return HttpResponseNotFound("Not found")
    if not (os.path.exists(fullpath) and os.path.isfile(fullpath)):
        return HttpResponseNotFound("Not found")

    stat = os.stat(fullpath)
    content_type, _ = mimetypes.guess_type(fullpath)
    if not content_type:
        content_type = "application/octet-stream"

    # HEAD = headers only
    if request.method == "HEAD":
        resp = HttpResponse(content_type=content_type)
        resp["Content-Length"] = str(stat.st_size)
        resp["Last-Modified"] = http_date(stat.st_mtime)
        return _add_cors_headers(resp)

    # Range support
    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE")
    if range_header:
        # e.g. "bytes=12345-"
        try:
            units, rng = range_header.strip().split("=", 1)
        except ValueError:
            units, rng = "bytes", ""
        if units == "bytes":
            start_str, end_str = (rng.split("-", 1) + [""])[:2]
            try:
                start = int(start_str) if start_str else 0
            except ValueError:
                start = 0
            try:
                end = int(end_str) if end_str else (stat.st_size - 1)
            except ValueError:
                end = stat.st_size - 1
            end = min(end, stat.st_size - 1)
            if start > end or start >= stat.st_size:
                resp = HttpResponse(status=416)  # Range Not Satisfiable
                resp["Content-Range"] = f"bytes */{stat.st_size}"
                return _add_cors_headers(resp)

            resp = StreamingHttpResponse(
                _open_file_range(fullpath, start, end),
                status=206,
                content_type=content_type,
            )
            resp["Content-Length"] = str(end - start + 1)
            resp["Content-Range"] = f"bytes {start}-{end}/{stat.st_size}"
            resp["Last-Modified"] = http_date(stat.st_mtime)
            return _add_cors_headers(resp)

    # No Range → full file
    resp = FileResponse(open(fullpath, "rb"), content_type=content_type)
    resp["Content-Length"] = str(stat.st_size)
    resp["Last-Modified"] = http_date(stat.st_mtime)
    return _add_cors_headers(resp)
