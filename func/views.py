from rest_framework.generics import GenericAPIView, UpdateAPIView
from rest_framework.response import Response
from .models import Draft, Saved
from .serializers import DraftSerializer, SavedSerializer
from rest_framework import response, status
from ftplib import FTP
import os
from django.http import JsonResponse, StreamingHttpResponse
import cloudinary.uploader

from django.core.files.storage import default_storage
from django.conf import settings
from .models import Video
import ffmpeg
from rest_framework.parsers import MultiPartParser


class VideoUploadView(GenericAPIView):
    parser_classes = [MultiPartParser]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        video_file = request.FILES.get('video')

        if not video_file:
            return Response({"error": "No video file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if not video_file.content_type.startswith("video/"):
            return Response({"error": "Only video files are allowed!"}, status=status.HTTP_400_BAD_REQUEST)

        if video_file.size > 500 * 1024 * 1024:
            return Response({"error": "File size too large. Maximum size is 500MB."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = cloudinary.uploader.upload_large(
                video_file,
                resource_type="video",
                format="mp4"
            )
            return Response({
                "message": "Video uploaded and transcoded successfully",
                "fileUrl": result.get("secure_url"),
                "mimetype": result.get("resource_type"),
                "size": result.get("bytes"),
            })
        except Exception as e:
            return Response({"error": "Failed to upload video", "details": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# app/views.py
import os
import requests
from urllib.parse import urlencode
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import status

import io, os, requests, ipaddress
from urllib.parse import urlparse
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

UNSPLASH_ACCESS_KEY = 't8RZUEKG7f0YKfH88DnhVWwnrJgXJ7U3yz8qNHKMWA0'
DEEPAI_API_KEY = 'b3919f4f-d522-46c0-8965-30b08849570c'


# --- Small helper to add permissive CORS headers on each response ---
def _cors(resp):
    resp["Access-Control-Allow-Origin"] = "*"  # or your exact frontend origin
    resp["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    resp["Vary"] = "Origin"
    return resp


class UnsplashSearchAPIView(APIView):
    authentication_classes = []
    """
    GET /api/unsplash/search?q=<query>&per_page=20
    """

    def options(self, request, *args, **kwargs):
        return _cors(JsonResponse({}, status=200))

    def get(self, request):
        if not UNSPLASH_ACCESS_KEY:
            resp = JsonResponse({"error": "UNSPLASH_ACCESS_KEY is not set on server."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return _cors(resp)

        q = request.GET.get("q", "nature")
        per_page = request.GET.get("per_page", "20")

        # Call Unsplash from the server (avoids browser CORS + keeps key secret)
        params = {
            "query": q,
            "per_page": per_page,
            "client_id": UNSPLASH_ACCESS_KEY,  # or use Authorization: Client-ID header
        }
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos?" + urlencode(params),
                timeout=15,
            )
            data = r.json()
            # Pass through as-is; front-end expects `results`
            resp = JsonResponse(data, status=r.status_code, safe=False)
            return _cors(resp)
        except requests.RequestException as e:
            resp = JsonResponse({"error": f"Unsplash request failed: {e}"},
                                status=status.HTTP_502_BAD_GATEWAY)
            return _cors(resp)


@method_decorator(csrf_exempt, name="dispatch")
class DeepAIText2ImgAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def options(self, request, *args, **kwargs):
        return _cors(JsonResponse({}, status=200))

    def post(self, request):
        if not DEEPAI_API_KEY:
            return _cors(JsonResponse({"error": "DEEPAI_API_KEY is not set on server."}, status=500))

        body = request.data if hasattr(request, "data") else {}
        text  = (body.get("text") or "").strip()
        style = (body.get("style") or "").strip()

        if not text:
            return _cors(JsonResponse({"error": "Field 'text' is required."}, status=400))

        prompt = f"{text}" if not style else f"{text}, style: {style}"

        try:
            r = requests.post(
                "https://api.deepai.org/api/text2img",
                data={"text": prompt},  # keep it minimal; DeepAI is strict
                headers={"api-key": DEEPAI_API_KEY},
                timeout=60,
            )
        except requests.RequestException as e:
            return _cors(JsonResponse({"error": f"DeepAI request failed: {e}"}, status=502))

        try:
            data = r.json()
        except ValueError:
            return _cors(JsonResponse({"error": "DeepAI returned non-JSON response."}, status=502))

        # Normalize possible success shapes:
        # - { output_url: "https://..." }
        # - { output: "https://..." }
        # - { output: ["https://...", ...] }
        output_url = None
        if isinstance(data.get("output_url"), str):
            output_url = data["output_url"]
        elif isinstance(data.get("output"), str):
            output_url = data["output"]
        elif isinstance(data.get("output"), list) and data["output"]:
            first = data["output"][0]
            if isinstance(first, str):
                output_url = first
            elif isinstance(first, dict) and isinstance(first.get("url"), str):
                output_url = first["url"]

        if not output_url or r.status_code != 200:
            msg = (
                data.get("status_msg")
                or data.get("error")
                or data.get("err")
                or f"DeepAI returned status {r.status_code} without an image URL"
            )
            # Return upstream for debugging in Network tab
            return _cors(JsonResponse({"error": msg, "upstream": data}, status=502))

        # Success: return a consistent shape
        return _cors(JsonResponse({"output_url": output_url}, status=200))



def _is_public_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        if p.scheme not in {"http", "https"}: return False
        host = p.hostname or ""
        try:
            ip = ipaddress.ip_address(host)
            return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local)
        except ValueError:
            # hostname string; allow
            return True
    except Exception:
        return False


class ImageProxyAPIView(APIView):
    """
    GET /api/proxy/image/?url=<encoded_image_url>
    Streams the remote image back with same-origin headers so canvas isn't tainted.
    """
    authentication_classes = []

    def options(self, request, *args, **kwargs):
        return _cors(JsonResponse({}, status=200))

    def get(self, request):
        raw_url = request.GET.get("url", "")
        if not raw_url or not _is_public_http_url(raw_url):
            return _cors(JsonResponse({"error": "Invalid 'url'."}, status=400))

        try:
            # Fetch image (no credentials), small timeout
            r = requests.get(raw_url, stream=True, timeout=15, headers={"User-Agent": "img-proxy/1.0"})
            if r.status_code != 200:
                return _cors(JsonResponse({"error": f"Upstream {r.status_code}"}, status=502))

            # Detect mime
            ctype = r.headers.get("Content-Type", "image/jpeg")
            data = r.content  # safe to buffer typical sizes; for very large, stream

            resp = HttpResponse(content=data, content_type=ctype, status=200)
            # CORS to allow drawImage and export
            _cors(resp)
            # Caching is nice to reduce API calls
            resp["Cache-Control"] = "public, max-age=86400"
            # Disallow sniffing
            resp["X-Content-Type-Options"] = "nosniff"
            return resp

        except requests.RequestException as e:
            return _cors(JsonResponse({"error": f"Fetch failed: {e}"}, status=502))

import io
import os
import uuid
import requests
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.http import JsonResponse
from django.utils.datastructures import MultiValueDictKeyError

from rest_framework.views import APIView
from rest_framework import status
from PIL import Image, ImageColor

import numpy as np
from rembg import remove


def _download_image_to_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.content


def _parse_bg_color(bg: Optional[str]):
    """
    Returns None for transparent; otherwise an (R, G, B, A) tuple.
    Accepts '#RRGGBB' or '#RRGGBBAA' or 'transparent'.
    """
    if not bg or str(bg).lower() == 'transparent':
        return None
    # Pillow's ImageColor.getcolor supports hex; default alpha to 255 if not given
    rgba = ImageColor.getcolor(bg, "RGBA")
    return rgba


class BackgroundRemoveAPIView(APIView):
    authentication_classes = []
    """
    POST /api/image/remove-bg

    Multipart form fields:
      - image: file (preferred)
      - image_url: URL (optional alternative to file)
      - bg: "transparent" (default) OR hex like "#ffffff" or "#ffffffff"
      - out_format: "png" (default) or "jpeg" (png recommended for transparency)

    Returns JSON: { "image_url": "<absolute url>", "width": int, "height": int }
    """
    def post(self, request, *args, **kwargs):
        try:
            image_bytes = None

            # 1) Prefer a posted file
            if 'image' in request.FILES:
                image_file = request.FILES['image']
                image_bytes = image_file.read()
            # 2) Fallback to URL
            elif 'image_url' in request.data and request.data.get('image_url'):
                image_bytes = _download_image_to_bytes(request.data['image_url'])
            else:
                return JsonResponse(
                    {"detail": "Provide 'image' file or 'image_url'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            bg = request.data.get('bg', 'transparent')
            out_format = (request.data.get('out_format') or 'png').lower()
            if out_format not in ('png', 'jpeg', 'jpg'):
                out_format = 'png'

            # Open original
            with Image.open(io.BytesIO(image_bytes)) as im:
                im = im.convert("RGBA")

            # Remove background to RGBA (transparent mask)
            arr = np.array(im)
            out_arr = remove(arr)  # returns BGRA or RGBA
            out_img = Image.fromarray(out_arr).convert("RGBA")

            # If bg color provided, composite on a solid background
            rgba = _parse_bg_color(bg)
            if rgba is not None:
                bg_layer = Image.new("RGBA", out_img.size, rgba)
                out_img = Image.alpha_composite(bg_layer, out_img)
                # If bg is opaque and output is JPEG, we can safely convert to RGB
                if out_format in ('jpeg', 'jpg'):
                    out_img = out_img.convert("RGB")
            else:
                # bg is transparent; if user asked for JPEG, flatten onto white
                if out_format in ('jpeg', 'jpg'):
                    white = Image.new("RGBA", out_img.size, (255, 255, 255, 255))
                    out_img = Image.alpha_composite(white, out_img).convert("RGB")

            # Save to MEDIA_ROOT
            ext = 'jpg' if out_format == 'jpeg' else out_format
            out_name = f"{uuid.uuid4().hex}.{ext}"
            out_dir = Path(settings.MEDIA_ROOT) / "processed"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / out_name

            # For PNG keep RGBA; for JPEG keep RGB
            save_params = {}
            if out_format in ('jpeg', 'jpg'):
                save_params['quality'] = 92
            out_img.save(out_path, **save_params)

            # Build absolute URL
            rel_url = f"{settings.MEDIA_URL}processed/{out_name}"
            abs_url = request.build_absolute_uri(rel_url)

            w, h = out_img.size
            return JsonResponse(
                {"image_url": abs_url, "width": w, "height": h},
                status=status.HTTP_200_OK
            )
        except requests.RequestException as e:
            return JsonResponse(
                {"detail": f"Failed to fetch image_url: {e}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except MultiValueDictKeyError:
            return JsonResponse(
                {"detail": "Missing required form fields."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return JsonResponse(
                {"detail": f"Unexpected error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


