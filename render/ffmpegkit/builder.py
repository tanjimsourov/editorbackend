from __future__ import annotations

import json
import subprocess
import os
from typing import List, Tuple, Literal

from .background import _bg_filters, _bg_image_filters
from .media import _media_filters
from .textdraw import _emit_text_overlay
from .audio import _audio_mix_filters
from .shapes.circle import _emit_circle_overlays
from .shapes.triangle import _emit_triangle_overlays
from .shapes.rectangle import _emit_rectangle_overlays
from .shapes.line import _emit_line_overlays
from .shapes.ellipse import _emit_ellipse_overlays
from .shapes.sign import _emit_sign_overlays
from .shapes.weather import _emit_weather_overlays

Mode = Literal["preview", "final"]

# Preview downscale cap (speed boost). Set to None to disable.
PREVIEW_MAX_DIM = (1280, 720)  # (W, H)

def _input_has_audio(src: str) -> bool:
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "json",
                src,
            ],
            stderr=subprocess.STDOUT,
        )
        data = json.loads(out.decode("utf-8", "ignore"))
        return bool(data.get("streams"))
    except Exception:
        return False


def _build_filtergraph_and_inputs(tl: dict, positive_duration: float) -> Tuple[
    str,               # filter_complex
    str,               # last_v label
    List[List[str]],   # input flags per input
    List[str],         # input srcs
    List[str],         # audio labels (may be empty)
    int,               # FPS
    int, int,          # W, H (output canvas before optional preview downscale)
]:
    W, H = int(tl["width"]), int(tl["height"])
    FPS = int(tl.get("fps", 30))
    tracks = sorted(tl.get("tracks", []), key=lambda t: t.get("z", 0))
    bg_color = tl.get("background") or "#000000"

    bg_image = tl.get("backgroundImage") or None
    bg_opacity = float(tl.get("backgroundOpacity") if tl.get("backgroundOpacity") is not None else 1.0)
    bg_fit = tl.get("backgroundFit") or "cover"

    # ---------------- Inputs ----------------
    input_flags: List[List[str]] = []
    input_srcs: List[str] = []

    bg_img_input_idx = None
    if bg_image:
        input_flags.append(["-loop", "1", "-t", f"{positive_duration}"])
        input_srcs.append(str(bg_image))
        bg_img_input_idx = 0

    for t in tracks:
        typ = t.get("type")
        if typ == "image":
            input_flags.append(["-loop", "1", "-t", f"{positive_duration}"])
            input_srcs.append(str(t["src"]))
            t["_in_idx"] = len(input_srcs) - 1
            t["_has_audio"] = False
        elif typ in ("video", "audio"):
            input_flags.append([])
            input_srcs.append(str(t["src"]))
            t["_in_idx"] = len(input_srcs) - 1
            t["_has_audio"] = _input_has_audio(t["src"])

    # ---------------- Filters ----------------
    filters: List[str] = []
    filters += _bg_filters(W, H, FPS, bg_color)  # solid color base
    last_v = "[base]"
    vcount = 0

    # Background image
    bg_filters, last_v = _bg_image_filters(bg_img_input_idx, last_v, W, H, bg_fit, bg_opacity)
    filters += bg_filters

    # Media
    media_filters, last_v, vcount, audio_labels = _media_filters(tracks, last_v, vcount)
    filters += media_filters

    # Text overlays
    for t in tracks:
        if t.get("type") in ("text", "datetime"):
            txt_filters, last_v, vcount = _emit_text_overlay(t, last_v, vcount)
            filters += txt_filters

    # Vector shapes
    for t in tracks:
        if t.get("type") == "circle":
            circ_filters, last_v, vcount = _emit_circle_overlays(t, last_v, vcount, FPS)
            filters += circ_filters
    for t in tracks:
        if t.get("type") == "triangle":
            tri_filters, last_v, vcount = _emit_triangle_overlays(t, last_v, vcount, FPS)
            filters += tri_filters
    for t in tracks:
        if t.get("type") == "rectangle":
            rect_filters, last_v, vcount = _emit_rectangle_overlays(t, last_v, vcount, FPS)
            filters += rect_filters
    for t in tracks:
        if t.get("type") == "line":
            line_filters, last_v, vcount = _emit_line_overlays(t, last_v, vcount, FPS)
            filters += line_filters
    for t in tracks:
        if t.get("type") == "ellipse":
            ell_filters, last_v, vcount = _emit_ellipse_overlays(t, last_v, vcount, FPS)
            filters += ell_filters

    # Sign / Weather
    for t in tracks:
        if t.get("type") == "sign":
            sign_filters, last_v, vcount = _emit_sign_overlays(t, last_v, vcount, FPS)
            filters += sign_filters
    for t in tracks:
        if t.get("type") == "weather":
            wx_filters, last_v, vcount = _emit_weather_overlays(t, last_v, vcount, FPS)
            filters += wx_filters

    filter_complex = ";".join(filters)
    return filter_complex, last_v, input_flags, input_srcs, audio_labels, FPS, W, H


def _encode_settings(mode: Mode) -> dict:
    """
    Returns encoding & system flags tuned for speed/quality by mode.
    """
    if mode == "preview":
        return {
            "preset": "ultrafast",
            "crf": "28",
            "extra": ["-tune", "zerolatency"],
        }
    # final
    return {
        "preset": "veryfast",
        "crf": "20",
        "extra": [],
    }


def _threading_flags() -> List[str]:
    # Let ffmpeg pick sensible defaults; still expose for clarity
    threads = "0"  # auto
    # Filter graph threading: use a conservative parallelism
    filter_threads = str(max(2, (os.cpu_count() or 4) // 2))
    return [
        "-threads", threads,
        "-filter_threads", filter_threads,
        "-filter_complex_threads", filter_threads,
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
    ]


def _maybe_add_preview_downscale(filter_complex: str, last_v: str, W: int, H: int, mode: Mode):
    """
    Optionally append a fast downscale for preview to speed encoding.
    Returns (filter_complex, last_v).
    """
    if mode != "preview" or not PREVIEW_MAX_DIM:
        return filter_complex, last_v

    maxW, maxH = PREVIEW_MAX_DIM
    if W <= maxW and H <= maxH:
        return filter_complex, last_v

    # Keep aspect — scale to fit within maxW x maxH using fast_bilinear
    # Compute with ffmpeg expressions:
    # if a >= b: w=maxW, h=-1 else h=maxH, w=-1
    vout = "[v_preview]"
    scale_expr = (
        f"{last_v}scale="
        f"'if(gt(a,{maxW}/{maxH}),{maxW},-2)':"
        f"'if(gt(a,{maxW}/{maxH}),-2,{maxH})'"
        f":flags=fast_bilinear{vout}"
    )
    new_fc = f"{filter_complex};{scale_expr}"
    return new_fc, vout


def build_ffmpeg_cmd(tl: dict, output_path: str, mode: Mode = "final") -> List[str]:
    """
    Build the VIDEO command (MP4).
    - Preview mode favors speed (ultrafast, higher CRF, optional downscale)
    - Final mode favors quality (veryfast, CRF 20)
    """
    FPS = int(tl.get("fps", 30))
    raw_D = float(tl.get("duration", 0.0))
    D = raw_D if raw_D > 0 else max(1.0 / max(FPS, 1), 0.0334)  # >= one frame

    filter_complex, last_v, input_flags, input_srcs, audio_labels, FPS, W, H = \
        _build_filtergraph_and_inputs(tl, D)

    # Optional downscale for preview to speed up encode
    filter_complex, last_v = _maybe_add_preview_downscale(filter_complex, last_v, W, H, mode)

    args: List[str] = []
    # inputs
    for flags, src in zip(input_flags, input_srcs):
        if not isinstance(flags, list):
            flags = []
        args += flags + ["-i", src]

    # threading + logging first for global impact
    args += _threading_flags()

    # filtergraph
    args += ["-filter_complex", filter_complex]

    # mapping
    map_args: List[str] = ["-map", last_v]
    if audio_labels:
        a_filters, afinal = _audio_mix_filters(audio_labels)
        # extend filter_complex VALUE
        try:
            fc_idx = args.index("-filter_complex")
            args[fc_idx + 1] = f"{filter_complex};{';'.join(a_filters)}"
        except ValueError:
            args += ["-filter_complex", f"{filter_complex};{';'.join(a_filters)}"]
        map_args += ["-map", afinal, "-c:a", "aac"]
    else:
        # No mixed audio; skip audio entirely in preview to speed up
        if mode == "preview":
            map_args += ["-an"]

    args += map_args

    # encoding settings
    enc = _encode_settings(mode)

    args += [
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", enc["preset"],
        "-crf", enc["crf"],
        "-pix_fmt", "yuv420p",
        *enc["extra"],
        "-movflags", "+faststart",
        "-t", f"{D}",
        "-shortest",
        "-y",
        output_path,
    ]
    return args


def build_ffmpeg_cmd_still(tl: dict, output_path: str, fmt: str = "png") -> List[str]:
    """
    Build a SINGLE-FRAME render (PNG/JPG).
    Also uses threading/log optimizations for snappier stills.
    """
    FPS = int(tl.get("fps", 30))
    D = max(1.0 / max(FPS, 1), 0.0334)

    filter_complex, last_v, input_flags, input_srcs, _audio_labels, FPS, W, H = \
        _build_filtergraph_and_inputs(tl, D)

    # For stills, optionally downscale if canvas is huge (keeps parity with preview look)
    filter_complex, last_v = _maybe_add_preview_downscale(filter_complex, last_v, W, H, mode="preview")

    args: List[str] = []
    for flags, src in zip(input_flags, input_srcs):
        if not isinstance(flags, list):
            flags = []
        args += flags + ["-i", src]

    args += _threading_flags()

    args += [
        "-filter_complex", filter_complex,
        "-map", last_v,
        "-frames:v", "1",
        "-f", "image2",
        "-y",
    ]

    if str(fmt).lower().endswith("png") or str(fmt).lower() == "png":
        args += ["-vcodec", "png", output_path]
    else:
        args += ["-q:v", "2", output_path]

    return args
