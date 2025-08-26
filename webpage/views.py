from urllib.parse import urlparse
import ipaddress
import os
import uuid
import shutil
import subprocess
import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from asgiref.sync import async_to_sync
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError


# ---- Optional: SSRF guard (keeps localhost/private nets out) ----
def _is_public_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = parsed.hostname or ""
        try:
            ip = ipaddress.ip_address(host)
            return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local)
        except ValueError:
            # Hostname (not an IP literal) — allow
            return True
    except Exception:
        return False


def _ffmpeg_bin() -> str:
    """
    Return ffmpeg binary path. Uses settings.FFMPEG_BIN if provided; otherwise uses PATH.
    """
    bin_from_settings = getattr(settings, "FFMPEG_BIN", None)
    if bin_from_settings:
        return bin_from_settings
    return shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_bin() -> str:
    """
    Return ffprobe binary path. Uses settings.FFPROBE_BIN if provided; otherwise uses PATH.
    """
    bin_from_settings = getattr(settings, "FFPROBE_BIN", None)
    if bin_from_settings:
        return bin_from_settings
    return shutil.which("ffprobe") or "ffprobe"


def _ffmpeg_exists() -> bool:
    return shutil.which(_ffmpeg_bin()) is not None or os.path.isabs(_ffmpeg_bin())


def _detect_leading_black(in_path: str) -> float:
    """
    Use ffmpeg blackdetect to estimate the length of initial black/blank frames.
    Returns seconds (float). If detection fails, returns 0.0.

    Notes:
    - We use strict detection for the beginning only.
    - 'white' pages often compress as very low-variance frames and also get flagged;
      this is fine for our 'blank' trim purpose.
    """
    ffmpeg = _ffmpeg_bin()
    try:
        # We limit to first ~8 seconds for speed
        # blackdetect params:
        #   d=0.10  -> minimal duration for a black segment
        #   pic_th=0.98 -> how close to black/white to consider (more strict)
        # We output to null and parse stderr.
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-ss", "0",
            "-t", "8",
            "-i", in_path,
            "-vf", "blackdetect=d=0.10:pic_th=0.98",
            "-f", "null",
            "-"
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        stderr = proc.stderr or ""
        # Look for the very first black segment near the beginning, and get its black_end
        # Example lines:
        # [blackdetect @ ...] black_start:0 black_end:1.92 black_duration:1.92
        first_match = re.search(r"black_start:\s*([0-9.]+)\s+black_end:\s*([0-9.]+)", stderr)
        if not first_match:
            return 0.0
        black_start = float(first_match.group(1))
        black_end = float(first_match.group(2))
        # Only count it if it starts near 0 (lead-in)
        if black_start <= 0.25:
            return max(0.0, black_end)
        return 0.0
    except Exception:
        return 0.0


# ---------- Screenshot helper ----------
async def _take_screenshot_bytes(
    url: str,
    device_scale_factor: float = 1.0,
    delay_ms: int = 0,
    timeout_ms: int = 30_000,
    viewport_w: int = 1920,
    viewport_h: int = 1080,
    full_page: bool = True,
) -> bytes:
    """
    Open the URL and return a PNG screenshot (bytes).
    device_scale_factor controls page scaling for sharper shots (eg 1.5, 2.0).
    delay_ms allows waiting for animations/lazy content before the shot.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": viewport_w, "height": viewport_h},
            device_scale_factor=device_scale_factor,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if delay_ms > 0:
                await page.wait_for_timeout(int(delay_ms))
            png = await page.screenshot(full_page=full_page, type="png")
            return png
        finally:
            await context.close()
            await browser.close()


def _trim_and_convert_with_ffmpeg(
    in_path: str,
    start_sec: float,
    fmt: str = "mp4",
) -> str:
    """
    Trim leading 'start_sec' seconds and (optionally) convert container/codec.
    We do accurate seek by putting -ss AFTER -i (re-encode).
    Returns output file path. If ffmpeg is missing or fails, returns input path.
    """
    if not _ffmpeg_exists():
        return in_path

    ffmpeg = _ffmpeg_bin()
    fmt = (fmt or "mp4").lower()
    out_dir = os.path.dirname(in_path)
    out_basename = f"{uuid.uuid4().hex}.{fmt}"
    out_path = os.path.join(out_dir, out_basename)

    # Accurate trim: -ss AFTER -i for re-encode seeking.
    if fmt == "mp4":
        cmd = [
            ffmpeg, "-hide_banner", "-y",
            "-i", in_path,
            "-ss", f"{max(0.0, start_sec):.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            out_path,
        ]
    elif fmt == "webm":
        cmd = [
            ffmpeg, "-hide_banner", "-y",
            "-i", in_path,
            "-ss", f"{max(0.0, start_sec):.3f}",
            "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0",
            "-c:a", "libopus",
            out_path,
        ]
    else:
        # Unknown format; default to mp4
        fmt = "mp4"
        out_path = os.path.join(out_dir, f"{uuid.uuid4().hex}.mp4")
        cmd = [
            ffmpeg, "-hide_banner", "-y",
            "-i", in_path,
            "-ss", f"{max(0.0, start_sec):.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            out_path,
        ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            os.remove(in_path)
        except Exception:
            pass
        return out_path
    except Exception:
        # On failure, keep the original
        return in_path


async def _capture_scroll_video(
    url: str,
    viewport_w: int = 1920,
    viewport_h: int = 1080,
    speed_pps: int = 180,     # pixels per second (reading speed)
    padding_ms: int = 800,    # tail padding (end only) so last fold is readable
    timeout_ms: int = 30000,
    out_format: str = "mp4",
) -> str:
    """
    Opens the URL at 1920x1080, records while auto-scrolling, then trims the
    video head to the page's First Contentful Paint (FCP) and any detected
    leading black/blank, so it starts on content.
    Returns absolute filesystem path to the final video.
    """
    # Temp dir where Playwright writes videos (it requires a directory)
    tmp_root = Path(settings.MEDIA_ROOT) / "tmp_playwright_videos"
    tmp_root.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={"width": viewport_w, "height": viewport_h},
            record_video_dir=str(tmp_root),
            record_video_size={"width": viewport_w, "height": viewport_h},
            device_scale_factor=1.0,
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
        )
        page = await context.new_page()

        try:
            # Navigate; recording starts before this, but we will trim later.
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for visible content (text or media) to be on screen
            await page.wait_for_function(
                """
                () => {
                  const b = document.body;
                  if (!b) return false;
                  const cs = getComputedStyle(b);
                  const visible = cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity || '1') > 0;
                  const hasText = (b.innerText || '').trim().length > 0;
                  const hasMedia = !!b.querySelector('img,svg,canvas,video');
                  return visible && (hasText || hasMedia);
                }
                """,
                timeout=timeout_ms,
            )

            # Grab First Contentful Paint (ms relative to navigationStart)
            fcp_ms = await page.evaluate(
                """
                () => {
                  const paints = performance.getEntriesByType('paint') || [];
                  const f = paints.find(p => p.name === 'first-contentful-paint');
                  return f ? f.startTime : 0;
                }
                """
            ) or 0

            # Two RAF ticks to ensure first painted frame is stable
            await page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

            # Measure document height & compute scrolling plan
            metrics = await page.evaluate(
                """() => {
                    const body = document.body;
                    const html = document.documentElement;
                    const scrollHeight = Math.max(
                      body.scrollHeight, body.offsetHeight,
                      html.clientHeight, html.scrollHeight, html.offsetHeight
                    );
                    const viewportH = window.innerHeight;
                    return { scrollHeight, viewportH };
                }"""
            )
            scroll_height = int(metrics["scrollHeight"])
            viewport_h_now = int(metrics["viewportH"])

            # Start at top (after content is ready)
            await page.evaluate("window.scrollTo(0, 0)")

            if scroll_height <= viewport_h_now:
                await page.wait_for_timeout(600)  # brief steady capture when no scroll is needed
            else:
                distance = scroll_height - viewport_h_now
                step_px = 40  # small smooth steps
                ms_per_step = int((step_px / max(1, speed_pps)) * 1000)

                scrolled = 0
                while scrolled < distance:
                    scrolled += step_px
                    await page.evaluate("(y) => window.scrollTo(0, y)", scrolled)
                    await page.wait_for_timeout(ms_per_step)

                # Ensure we’ve reached the bottom and let the viewer read the last fold
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(max(800, padding_ms))

            # Finalize recording. (Video file is resolved once the page is closed)
            video_obj = page.video
            await page.close()
            video_tmp_path = await video_obj.path()

        finally:
            await context.close()
            await browser.close()

    # Move raw webm to MEDIA_ROOT/webpage_videos/<uuid>.webm
    out_dir = Path(settings.MEDIA_ROOT) / "webpage_videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_webm_path = out_dir / f"{uuid.uuid4().hex}.webm"
    os.replace(video_tmp_path, raw_webm_path)

    # Compute trim seconds:
    # 1) FCP in seconds, shave a tiny 50ms pre-roll
    fcp_sec = max(0.0, float((fcp_ms or 0)) / 1000.0 - 0.05)
    # 2) Detect black/blank lead
    black_lead_sec = _detect_leading_black(str(raw_webm_path))
    # Final start = the later of the two (plus a tiny safety 30ms)
    start_sec = max(fcp_sec, black_lead_sec) + 0.03

    # Convert/trim to requested format (default mp4) using accurate seek
    final_path = _trim_and_convert_with_ffmpeg(str(raw_webm_path), start_sec, out_format)

    return final_path


@method_decorator(csrf_exempt, name="dispatch")  # remove if you handle CSRF tokens
class ScreenshotAPIView(APIView):
    authentication_classes = []
    """
    GET/POST params:
      - url (required)
      - mode: "video" (default) or "screenshot"
      - device_scale (float, default=1.0)    [screenshot only]
      - delay_ms (int, default=0)            [screenshot only]
      - timeout_ms (int, default=30000)

      - speed_pps (int, default=180)         [video]
      - padding_ms (int, default=800)        [video] end padding only
      - format: "mp4" | "webm" (default "mp4")
      - download (bool, default=false)       [video] stream file inline if true
    """

    def get(self, request, *args, **kwargs):
        return self._handle_request(request)

    def post(self, request, *args, **kwargs):
        return self._handle_request(request)

    def _handle_request(self, request):
        mode = (request.query_params.get("mode") or request.data.get("mode") or "video").lower()
        url = request.query_params.get("url") or request.data.get("url")
        if not url:
            return Response({"error": "Missing 'url' parameter"}, status=status.HTTP_400_BAD_REQUEST)
        if not _is_public_http_url(url):
            return Response({"error": "Only public http(s) URLs are allowed."}, status=status.HTTP_400_BAD_REQUEST)

        timeout_ms = request.query_params.get("timeout_ms") or request.data.get("timeout_ms", 30000)

        # VIDEO params
        speed_pps = request.query_params.get("speed_pps") or request.data.get("speed_pps", 180)
        padding_ms = request.query_params.get("padding_ms") or request.data.get("padding_ms", 800)
        download = str(request.query_params.get("download") or request.data.get("download") or "false").lower() == "true"
        out_format = (request.query_params.get("format") or request.data.get("format") or "mp4").lower()

        # SCREENSHOT params (backward compatibility)
        device_scale = request.query_params.get("device_scale") or request.data.get("device_scale", 1.0)
        delay_ms = request.query_params.get("delay_ms") or request.data.get("delay_ms", 0)

        # Validate numerics
        try:
            timeout_ms = int(timeout_ms)
            speed_pps = int(speed_pps)
            padding_ms = int(padding_ms)
            device_scale = float(device_scale)
            delay_ms = int(delay_ms)
        except ValueError:
            return Response({"error": "Invalid numeric parameter(s)."}, status=status.HTTP_400_BAD_REQUEST)

        if mode == "video":
            try:
                video_fs_path = async_to_sync(_capture_scroll_video)(
                    url=url,
                    viewport_w=1920,
                    viewport_h=1080,
                    speed_pps=max(60, speed_pps),     # enforce a sane lower bound
                    padding_ms=max(200, padding_ms),  # end padding only
                    timeout_ms=timeout_ms,
                    out_format=out_format,
                )
            except PWTimeoutError:
                return Response({"error": "Page load timed out."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
            except Exception as e:
                return Response({"error": f"Failed to capture video: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            rel_path = os.path.relpath(video_fs_path, settings.MEDIA_ROOT).replace("\\", "/")
            media_url = (settings.MEDIA_URL or "/media/").rstrip("/")
            public_url = request.build_absolute_uri(f"{media_url}/{rel_path}")

            if download:
                mime = "video/mp4" if video_fs_path.lower().endswith(".mp4") else "video/webm"
                resp = FileResponse(open(video_fs_path, "rb"), content_type=mime)
                resp["Content-Disposition"] = f'inline; filename="webpage_capture.{video_fs_path.split(".")[-1]}"'
                return resp

            return Response(
                {
                    "url": public_url,
                    "path": rel_path,
                    "width": 1920,
                    "height": 1080,
                    "format": out_format,
                    "note": "Head trimmed to FCP and detected blank frames for zero white intro.",
                },
                status=status.HTTP_200_OK,
            )

        elif mode == "screenshot":
            try:
                png = async_to_sync(_take_screenshot_bytes)(
                    url=url,
                    device_scale_factor=device_scale,
                    delay_ms=delay_ms,
                    timeout_ms=timeout_ms,
                )
            except PWTimeoutError:
                return Response({"error": "Page load timed out."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
            except Exception as e:
                return Response({"error": f"Failed to capture screenshot: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            resp = HttpResponse(png, content_type="image/png")
            resp["Content-Disposition"] = 'inline; filename="screenshot.png"'
            return resp

        else:
            return Response({"error": "Invalid 'mode'. Use 'video' or 'screenshot'."}, status=status.HTTP_400_BAD_REQUEST)
