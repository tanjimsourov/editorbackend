# ffmpegkit/shapes/sign.py
import math
from ..colors import _ff_color, _drawtext_font_opt, _esc_text
from .rectangle import _rectangle_clip
from .triangle import _triangle_clip
from .circle import _circle_clip


def _pick(d: dict, *keys, default=None):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def _symbol_char(symbol_type: str | None, custom: str | None) -> str:
    """
    Map common symbol types to unicode. Fallback to custom symbol if provided.
    """
    if custom:
        return str(custom)
    st = (symbol_type or "").strip().lower()
    return {
        "copyright": "©",
        "registered": "®",
        "trademark": "™",
        "service": "℠",
        "paragraph": "§",
        "sound": "℗",
        "info": "ℹ",
    }.get(st, "©")


def _emit_sign_overlays(t: dict, last_v: str, vcount: int, fps: int):
    """
    Compose a 'sign' panel off-screen at size (w x h), render components, optionally rotate, then overlay.
    (x,y) is treated as the top-left of the UNROTATED sign (like rectangle).
    Rotation occurs around the sign's center.
    """
    filters = []

    # Geometry and timing
    x = int(round(float(t.get("x", 0))))
    y = int(round(float(t.get("y", 0))))
    w = int(max(1, round(float(t.get("width", 200)))))
    h = int(max(1, round(float(t.get("height", 100)))))
    rot_deg = float(t.get("rotation", 0.0))
    rot_rad = rot_deg * math.pi / 180.0
    enable = f"enable='between(t,{t['start']},{t['end']})'"

    # Opacity: multiply final alpha by overall opacity
    overall_opacity = float(_pick(t, "opacity", default=1.0))
    overall_opacity = max(0.0, min(1.0, overall_opacity))

    # Component toggles and styling
    sc = t.get("showComponents") or {}
    show_bg = bool(sc.get("background"))
    show_border = bool(sc.get("border"))
    show_text = bool(sc.get("text"))
    show_symbol = bool(sc.get("symbol"))
    show_icon = bool(sc.get("icon"))
    show_arrow = bool(sc.get("arrow"))

    cols = t.get("colors") or {}
    col_bg = _pick(cols, "background", default=None)  # None -> transparent
    col_text = _pick(cols, "text", default="#000000")
    col_border = _pick(cols, "border", default="#000000")
    col_icon = _pick(cols, "icon", default=col_text)
    col_arrow = _pick(cols, "arrow", default=col_text)
    col_symbol = _pick(cols, "symbol", default=col_text)

    # Sizes
    fs_cfg = t.get("fontSizes") or {}
    fs_text = int(max(1, round(float(fs_cfg.get("text") or min(h * 0.35, 48)))))
    fs_symbol = int(max(1, round(float(fs_cfg.get("symbol") or min(h * 0.40, 56)))))
    icon_size = int(max(1, round(float(t.get("iconSize") or min(h * 0.40, 36)))))

    # Layout helpers
    margin = int(max(4, round(h * 0.08)))
    border_w = 2  # fixed for now
    bg_radius = int(round(h * 0.12))

    # 1) Base transparent canvas for the sign
    base = f"sign_base_{vcount}"
    filters.append(f"color=c=black@0:s={w}x{h}:r={fps},format=rgba[{base}]")
    vo = f"[v{vcount}_sign_0]"
    filters.append(f"[{base}]copy{vo}")
    vcount += 1

    # 2) Background (rounded rectangle)
    if show_bg and col_bg:
        label_bg = f"sign_bg_{vcount}"
        filters.append(
            _rectangle_clip(label_bg, w, h, col_bg, 1.0, fps, radius=bg_radius, inner_offset=0, only_border=False))
        vo2 = f"[v{vcount}_sign_bg]"
        filters.append(f"{vo}[{label_bg}]overlay=0:0{vo2}")
        vo = vo2
        vcount += 1

    # 3) Border (rounded rectangle outline)
    if show_border:
        label_bor = f"sign_bor_{vcount}"
        filters.append(_rectangle_clip(label_bor, w, h, col_border or "#000000", 1.0, fps,
                                       radius=bg_radius, inner_offset=max(1, border_w), only_border=True))
        vo2 = f"[v{vcount}_sign_bor]"
        filters.append(f"{vo}[{label_bor}]overlay=0:0{vo2}")
        vo = vo2
        vcount += 1

    # 4) Icon (filled circle) at left center
    if show_icon:
        r = max(1, icon_size // 2)
        d = r * 2
        icon_label = f"sign_icon_{vcount}"
        filters.append(_circle_clip(icon_label, d, r, col_icon or "#000000", 1.0, fps))
        cx = margin + r
        cy = h // 2
        vo2 = f"[v{vcount}_sign_icon]"
        filters.append(f"{vo}[{icon_label}]overlay={cx - r}:{cy - r}{vo2}")
        vo = vo2
        vcount += 1

    # 5) Arrow (triangle) at right center
    if show_arrow:
        tw = int(max(6, round(h * 0.35)))
        th = int(max(6, round(h * 0.35)))
        arr_label = f"sign_arrow_{vcount}"
        filters.append(_triangle_clip(arr_label, tw, th, col_arrow or "#000000", 1.0, "right", fps))
        ax = w - margin - tw
        ay = (h - th) // 2
        vo2 = f"[v{vcount}_sign_arrow]"
        filters.append(f"{vo}[{arr_label}]overlay={ax}:{ay}{vo2}")
        vo = vo2
        vcount += 1

    # 6) Symbol and Text (center-aligned stack)
    if show_symbol or show_text:
        font_opt = _drawtext_font_opt(t)
        gap = int(round(h * 0.05))

        if show_symbol and show_text:
            sym_char = _esc_text(_symbol_char(t.get("symbolType"), t.get("customSymbol")))
            vo2 = f"[v{vcount}_sign_sym]"
            filters.append(
                f"{vo}drawtext={font_opt}:text='{sym_char}':"
                f"fontsize={fs_symbol}:fontcolor={_ff_color(col_symbol or col_text, None)}:"
                f"x=(w-text_w)/2:y=(h/2 - {gap})-text_h{vo2}"
            )
            vo = vo2
            vcount += 1

            text = _esc_text(str(t.get("text") or ""))
            vo2 = f"[v{vcount}_sign_txt]"
            filters.append(
                f"{vo}drawtext={font_opt}:text='{text}':"
                f"fontsize={fs_text}:fontcolor={_ff_color(col_text or '#000', None)}:"
                f"x=(w-text_w)/2:y=(h/2 + {gap}){vo2}"
            )
            vo = vo2
            vcount += 1

        elif show_symbol:
            sym_char = _esc_text(_symbol_char(t.get("symbolType"), t.get("customSymbol")))
            vo2 = f"[v{vcount}_sign_sym2]"
            filters.append(
                f"{vo}drawtext={font_opt}:text='{sym_char}':"
                f"fontsize={fs_symbol}:fontcolor={_ff_color(col_symbol or col_text, None)}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2{vo2}"
            )
            vo = vo2
            vcount += 1

        elif show_text:
            text = _esc_text(str(t.get("text") or ""))
            vo2 = f"[v{vcount}_sign_txt2]"
            filters.append(
                f"{vo}drawtext={font_opt}:text='{text}':"
                f"fontsize={fs_text}:fontcolor={_ff_color(col_text or '#000', None)}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2{vo2}"
            )
            vo = vo2
            vcount += 1

    # 7) Apply overall opacity (✅ fixed: use aa=<factor>, not aa*factor)
    vo_op = f"[v{vcount}_sign_alpha]"
    filters.append(f"{vo}format=rgba,colorchannelmixer=aa={overall_opacity:.3f}{vo_op}")
    vo = vo_op
    vcount += 1

    # 8) Rotate around center and overlay at (x,y)
    vo_rot = f"[v{vcount}_sign_rot]"
    filters.append(f"{vo}rotate={rot_rad}:ow=rotw(iw):oh=roth(ih):c=black@0{vo_rot}")
    vcount += 1

    # Center wants to land at (x + w/2, y + h/2). Use overlay vars w/h (overlay size), not W/H (main size).
    cx = x + w / 2.0
    cy = y + h / 2.0
    vo_out = f"[v{vcount}_sign_out]"
    filters.append(f"{last_v}{vo_rot}overlay={cx}-w/2:{cy}-h/2:{enable}{vo_out}")
    last_v = vo_out
    vcount += 1

    return filters, last_v, vcount
