from __future__ import annotations

import json
import subprocess
from typing import List

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


def _input_has_audio(src: str) -> bool:
    """
    Return True if `src` (local path or URL) contains at least one audio stream.
    If probing fails, returns False to keep the graph safe.
    """
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


def _build_filtergraph_and_inputs(tl: dict, positive_duration: float) -> tuple[
    str,                     # filter_complex
    str,                     # last_v label
    list[list[str]],         # input flags
    list[str],               # input srcs
    list[str],               # audio labels (may be empty)
    int,                     # FPS
]:
    """
    Shared core that:
      - assembles inputs (looping stills to match a tiny positive duration)
      - builds the video filter graph (base + media + text + shapes)
      - returns audio label list (for the video builder to mix if desired)
    """
    W, H = int(tl["width"]), int(tl["height"])
    FPS = int(tl.get("fps", 30))
    tracks = sorted(tl.get("tracks", []), key=lambda t: t.get("z", 0))
    bg_color = tl.get("background") or "#000000"

    # Optional background image support
    bg_image = tl.get("backgroundImage") or None
    bg_opacity = float(tl.get("backgroundOpacity") if tl.get("backgroundOpacity") is not None else 1.0)
    bg_fit = tl.get("backgroundFit") or "cover"

    # ---------------- Inputs ----------------
    input_flags: List[List[str]] = []
    input_srcs: List[str] = []

    bg_img_input_idx = None
    if bg_image:
        # loop a still so ffmpeg has a timebase to evaluate overlays at t=0
        input_flags.append(["-loop", "1", "-t", f"{positive_duration}"])
        input_srcs.append(str(bg_image))
        bg_img_input_idx = 0  # background image is first input

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
        # other types add no new inputs

    # ---------------- Filters ----------------
    filters: List[str] = []
    filters += _bg_filters(W, H, FPS, bg_color)
    last_v = "[base]"
    vcount = 0

    # Background image, if any
    bg_filters, last_v = _bg_image_filters(bg_img_input_idx, last_v, W, H, bg_fit, bg_opacity)
    filters += bg_filters

    # Media (videos/images + AUDIO label collection)
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
    return filter_complex, last_v, input_flags, input_srcs, audio_labels, FPS


def build_ffmpeg_cmd(tl: dict, output_path: str) -> List[str]:
    """
    Build the normal VIDEO command (MP4).
    Safe for zero/very short durations by bumping to 1/FPS.
    """
    FPS = int(tl.get("fps", 30))
    raw_D = float(tl.get("duration", 0.0))
    D = raw_D if raw_D > 0 else max(1.0 / max(FPS, 1), 0.0334)  # ~minimum one frame

    filter_complex, last_v, input_flags, input_srcs, audio_labels, FPS = \
        _build_filtergraph_and_inputs(tl, D)

    args: List[str] = []
    for flags, src in zip(input_flags, input_srcs):
        args += flags + ["-i", src]

    args += ["-filter_complex", filter_complex, "-map", last_v]

    # Audio: only map/mix when present
    if audio_labels:
        a_filters, afinal = _audio_mix_filters(audio_labels)
        # append the mix to filter_complex
        args[-1] = f"{filter_complex};{';'.join(a_filters)}"  # extend filter graph
        args += ["-map", afinal, "-c:a", "aac"]

    args += [
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-movflags", "+faststart",
        "-t", f"{D}",
        "-shortest",
        "-y",
        output_path,
    ]
    return args


def build_ffmpeg_cmd_still(tl: dict, output_path: str, fmt: str = "png") -> List[str]:
    """
    Build a SINGLE-FRAME render command that writes a PNG/JPG.
    - Reuses the full filter graph so image matches video look.
    - No audio mapping.
    - No -t / -shortest; we output exactly one frame.
    """
    FPS = int(tl.get("fps", 30))
    # tiny positive duration so videos/images that need time are valid at t=0
    D = max(1.0 / max(FPS, 1), 0.0334)

    filter_complex, last_v, input_flags, input_srcs, _audio_labels, FPS = \
        _build_filtergraph_and_inputs(tl, D)

    args: List[str] = []
    for flags, src in zip(input_flags, input_srcs):
        args += flags + ["-i", src]

    args += [
        "-filter_complex", filter_complex,
        "-map", last_v,
        "-frames:v", "1",
        "-f", "image2",
        "-y",
    ]

    if fmt.lower() in ("png", ".png"):
        args += ["-vcodec", "png", output_path]
    else:
        # jpg / jpeg
        args += ["-q:v", "2", output_path]

    return args
