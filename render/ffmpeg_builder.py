import os
import re

# ---------- Common helpers ----------

def _esc_text(s: str) -> str:
    s = s or ""
    s = s.replace("\\", "\\\\")
    s = s.replace(":", r"\:")
    s = s.replace("'", r"\'")
    return s


def _parse_hex_color(hex_str: str):
    if not isinstance(hex_str, str):
        return None, None
    hs = hex_str.strip()
    if not hs.startswith("#"):
        return None, None
    hs = hs[1:]
    if len(hs) == 3:
        hs = "".join(c * 2 for c in hs)
    if len(hs) == 4:  # #rgba
        hs = "".join(c * 2 for c in hs)
    if len(hs) == 6:
        rgb = hs
        a = None
    elif len(hs) == 8:
        rgb = hs[:6]
        try:
            a = int(hs[6:8], 16) / 255.0
        except ValueError:
            a = None
    else:
        return None, None
    return f"0x{rgb}", a


_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([0-9]*\.?[0-9]+)\s*)?\)",
    flags=re.IGNORECASE,
)


def _parse_rgb_func(s: str):
    if not isinstance(s, str):
        return None, None
    m = _RGB_RE.match(s.strip())
    if not m:
        return None, None
    r, g, b = (max(0, min(255, int(m.group(i)))) for i in (1, 2, 3))
    a = float(m.group(4)) if m.group(4) is not None else None
    rgb_hex = f"0x{r:02X}{g:02X}{b:02X}"
    return rgb_hex, a


def _ff_color(c: str | None, alpha_override: float | None = None) -> str:
    """
    Normalize CSS-like color to ffmpeg-friendly:
      - #rgb/#rgba/#rrggbb/#rrggbbaa
      - rgb(r,g,b) / rgba(r,g,b,a)
      - named colors pass through
    Returns '0xRRGGBB' or '0xRRGGBB@A.AAA' or 'name@A.AAA'
    """
    if not c:
        c = "white"
    c = c.strip()

    # Try hex forms
    rgb_hex, a = _parse_hex_color(c)
    if not rgb_hex:
        # Try rgb()/rgba()
        rgb_hex, a = _parse_rgb_func(c)

    # If we parsed to hex, optionally apply alpha
    if rgb_hex:
        if alpha_override is not None:
            a = max(0.0, min(1.0, float(alpha_override)))
        return f"{rgb_hex}@{a:.3f}" if a is not None else rgb_hex

    # Fall back to color names; add @alpha if provided
    if alpha_override is not None:
        a = max(0.0, min(1.0, float(alpha_override)))
        return f"{c}@{a:.3f}"
    return c


def _drawtext_font_opt(t: dict) -> str:
    font_path = t.get("fontPath")
    font_family = t.get("fontFamily") or "Arial"

    # 1) explicit fontPath from client
    if font_path and os.path.isfile(font_path):
        safe_path = font_path.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    # 2) Windows system Arial
    win_arial = r"C:\Windows\Fonts\arial.ttf"
    if os.name == "nt" and os.path.isfile(win_arial):
        safe_path = win_arial.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    # 3) Linux DejaVu (very common in containers)
    linux_dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.isfile(linux_dejavu):
        safe_path = linux_dejavu.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    # 4) fallback (may trigger fontconfig warning but will still try)
    return f"font='{font_family}'"


# ---------- Builders per content ----------

def _bg_filters(W: int, H: int, FPS: int, bg_color: str):
    return [f"color=c={_ff_color(bg_color)}:s={W}x{H}:r={FPS}[base]"]


def _bg_image_filters(bg_img_input_idx, last_v, W, H, fit: str, opacity: float):
    if bg_img_input_idx is None:
        return [], last_v
    vin = f"[{bg_img_input_idx}:v]"
    tmp = "[bgscaled]"
    foar = "increase" if fit == "cover" else ("decrease" if fit == "contain" else None)
    alpha = max(0.0, min(1.0, float(opacity)))
    filters = []
    if foar == "increase":
        filters.append(
            f"{vin}scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},format=rgba,colorchannelmixer=aa={alpha}{tmp}"
        )
    elif foar == "decrease":
        filters.append(
            f"{vin}scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"format=rgba,colorchannelmixer=aa={alpha}{tmp}"
        )
    else:
        filters.append(f"{vin}scale={W}:{H},format=rgba,colorchannelmixer=aa={alpha}{tmp}")
    vo = "[vbg]"
    filters.append(f"{last_v}{tmp}overlay=0:0{vo}")
    return filters, vo


def _media_filters(tracks, last_v, vcount):
    filters = []
    audio_labels = []
    for t in tracks:
        typ = t.get("type")
        if typ in ("video", "image"):
            idx = t["_in_idx"]
            vin = f"[{idx}:v]"
            vs = f"[v{vcount}s]"
            vo = f"[v{vcount}o]"

            if typ == "video":
                vtrim = "setpts=PTS-STARTPTS"
                if t.get("srcIn") is not None or t.get("srcOut") is not None:
                    si = t.get("srcIn") or 0
                    so = t.get("srcOut")
                    if so is not None and so > si:
                        vtrim = f"trim=start={si}:end={so},setpts=PTS-STARTPTS"
            else:
                vtrim = "setpts=PTS-STARTPTS"

            filters.append(f"{vin}scale={int(t['w'])}:{int(t['h'])},format=rgba,{vtrim}{vs}")
            enable = f"enable='between(t,{t['start']},{t['end']})'"
            x, y = int(t.get("x", 0)), int(t.get("y", 0))
            filters.append(f"{last_v}{vs}overlay={x}:{y}:{enable}{vo}")
            last_v = vo
            vcount += 1

        if typ in ("video", "audio"):
            idx = t["_in_idx"]
            ain = f"[{idx}:a]"
            ao = f"[a{idx}]"
            vol = float(t.get("volume", 1.0))
            muted = bool(t.get("muted", False))
            gain = 0.0 if muted else max(0.0, min(1.0, vol))

            atrim = "asetpts=PTS-STARTPTS"
            if t.get("srcIn") is not None or t.get("srcOut") is not None:
                si = t.get("srcIn") or 0
                so = t.get("srcOut")
                if so is not None and float(so) > float(si):
                    atrim = f"atrim=start={si}:end={so},asetpts=PTS-STARTPTS"

            delay_ms = max(0, int(round(float(t["start"]) * 1000)))
            filters.append(f"{ain}{atrim},adelay={delay_ms}:all=1,volume={gain:.3f}{ao}")
            audio_labels.append(ao)

    return filters, last_v, vcount, audio_labels


def _emit_text_overlay(t: dict, last_v: str, vcount: int):
    filters = []
    vo = f"[vtxt{vcount}]"
    enable = f"enable='between(t,{t['start']},{t['end']})'"
    font_opt = _drawtext_font_opt(t)
    fontcolor = _ff_color(t.get("color") or "white", None)
    fs = int(t.get("fontSize", 48))
    x, y = int(t.get("x", 0)), int(t.get("y", 0))

    stroke = ""
    if t.get("strokeColor") and float(t.get("strokeWidth") or 0) > 0:
        stroke = f":borderw={float(t['strokeWidth'])}:bordercolor={_ff_color(t['strokeColor'])}"

    box_part = ""
    bgColor = (t.get("bgColor") or "").strip() if isinstance(t.get("bgColor"), str) else None
    if bgColor:
        boxcolor = _ff_color(bgColor, None)
        pad = int(t.get("padding", 6) or 0)
        box_part = f":box=1:boxcolor={boxcolor}:boxborderw={max(0, pad)}"

    txt = _esc_text(str(t.get("text", "")))

    filters.append(
        f"{last_v}drawtext={font_opt}:text='{txt}':x={x}:y={y}:fontsize={fs}"
        f":fontcolor={fontcolor}{stroke}{box_part}:{enable}{vo}"
    )
    return filters, vo, vcount + 1


def _audio_mix_filters(audio_labels):
    if len(audio_labels) == 0:
        return ["anullsrc=channel_layout=stereo:sample_rate=48000[aout]"], "[aout]"
    if len(audio_labels) == 1:
        return [], audio_labels[0]
    return ["".join(audio_labels) + f"amix=inputs={len(audio_labels)}:normalize=1[aout]"], "[aout]"


# ---------- Circle helpers (vector) ----------

def _circle_clip(label: str, d: int, r: int, color: str, alpha: float, fps: int) -> str:
    col = _ff_color(color, alpha)
    return (
        f"color=c={col}:s={d}x{d}:r={fps},format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
        f"a='if(lte((X-{r})*(X-{r})+(Y-{r})*(Y-{r}),{r * r}),255,0)'[{label}]"
    )


def _emit_circle_overlays(t: dict, last_v: str, vcount: int, fps: int):
    filters = []
    cx = int(round(float(t.get("x", 0))))
    cy = int(round(float(t.get("y", 0))))
    r = int(max(1, round(float(t.get("radius", 10)))))
    d = r * 2
    enable = f"enable='between(t,{t['start']},{t['end']})'"

    stroke_w = int(max(0, round(float(t.get("outlineWidth") or 0))))
    stroke_color = t.get("outline")
    opac = float(t.get("opacity", 1.0))
    vo = last_v

    if stroke_w > 0 and stroke_color:
        r_outer = r
        label_outer = f"circ_stroke_{vcount}"
        filters.append(_circle_clip(label_outer, d, r_outer, stroke_color, opac, fps))
        x0 = cx - r_outer
        y0 = cy - r_outer
        vo2 = f"[v{vcount}_circ_s]"
        filters.append(f"{vo}[{label_outer}]overlay={x0}:{y0}:{enable}{vo2}")
        vo = vo2
        vcount += 1

    fill_color = t.get("fill") or "#000000"
    r_fill = max(0, r - max(0, stroke_w)) if (stroke_w > 0 and stroke_color) else r
    d_fill = r_fill * 2
    label_fill = f"circ_fill_{vcount}"
    filters.append(_circle_clip(label_fill, d_fill, r_fill, fill_color, opac, fps))
    x1 = cx - r_fill
    y1 = cy - r_fill
    vo2 = f"[v{vcount}_circ_f]"
    filters.append(f"{vo}[{label_fill}]overlay={x1}:{y1}:{enable}{vo2}")
    vo = vo2
    vcount += 1

    return filters, vo, vcount


# ---------- Triangle helpers (vector) ----------

def _tri_vertices(w: int, h: int, direction: str):
    # Local clip coordinates
    if direction == "down":
        return (0, 0), (w, 0), (w // 2, h)
    if direction == "left":
        return (0, h // 2), (w, 0), (w, h)
    if direction == "right":
        return (0, 0), (w, h // 2), (0, h)
    # default "up"
    return (w // 2, 0), (0, h), (w, h)


def _inside_tri_expr(v0, v1, v2):
    """
    Return an expression that evaluates to 1 when (X,Y) is inside the triangle, else 0.
    Uses barycentric sign tests but combines with numeric booleans (no and/or/not).
    """
    v0x, v0y = v0
    v1x, v1y = v1
    v2x, v2y = v2

    s1 = f"((X-{v2x})*({v1y}-{v2y})-(Y-{v2y})*({v1x}-{v2x}))"
    s2 = f"((X-{v0x})*({v2y}-{v0y})-(Y-{v0y})*({v2x}-{v0x}))"
    s3 = f"((X-{v1x})*({v0y}-{v1y})-(Y-{v1y})*({v0x}-{v1x}))"

    # Inside if all three have same sign (all >=0) OR (all <=0).
    pos = f"(gte({s1},0)*gte({s2},0)*gte({s3},0))"
    neg = f"(lte({s1},0)*lte({s2},0)*lte({s3},0))"
    # Convert to 0/1 by >0
    return f"gt({pos}+{neg},0)"


def _triangle_clip(label: str, w: int, h: int, color: str, alpha: float, direction: str, fps: int,
                   inner_offset: int = 0, only_border: bool = False) -> str:
    """
    Create a w×h RGBA clip with a filled triangle (or border) using geq alpha mask.
    If only_border=True, alpha=255 where inside(outer) && !inside(inner).
    inner_offset shrinks the inner triangle.
    """
    col = _ff_color(color, alpha)
    v0, v1, v2 = _tri_vertices(w, h, direction)
    if inner_offset > 0:
        # Simple inward offset approximation for cardinal triangles
        if direction == "up":
            vi0 = (w // 2, inner_offset)
            vi1 = (inner_offset, h - inner_offset)
            vi2 = (w - inner_offset, h - inner_offset)
        elif direction == "down":
            vi0 = (inner_offset, inner_offset)
            vi1 = (w - inner_offset, inner_offset)
            vi2 = (w // 2, h - inner_offset)
        elif direction == "left":
            vi0 = (inner_offset, h // 2)
            vi1 = (w - inner_offset, inner_offset)
            vi2 = (w - inner_offset, h - inner_offset)
        else:  # right
            vi0 = (inner_offset, inner_offset)
            vi1 = (w - inner_offset, h // 2)
            vi2 = (inner_offset, h - inner_offset)
    else:
        vi0 = v0
        vi1 = v1
        vi2 = v2

    inside_outer = _inside_tri_expr(v0, v1, v2)   # -> 0/1
    inside_inner = _inside_tri_expr(vi0, vi1, vi2)  # -> 0/1

    if only_border and inner_offset > 0:
        # border = outer && !inner  =>  outer * (1 - inner)
        mask = f"(({inside_outer})*(1-({inside_inner})))"
    else:
        # fill the inner region
        mask = f"({inside_inner})"

    a_expr = f"if({mask},255,0)"

    return (
        f"color=c={col}:s={w}x{h}:r={fps},format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{a_expr}'[{label}]"
    )


def _emit_triangle_overlays(t: dict, last_v: str, vcount: int, fps: int):
    filters = []
    x = int(round(float(t.get("x", 0))))
    y = int(round(float(t.get("y", 0))))
    w = int(max(1, round(float(t.get("width", 100)))))
    h = int(max(1, round(float(t.get("height", 100)))))
    direction = (t.get("direction") or "up").lower()
    enable = f"enable='between(t,{t['start']},{t['end']})'"
    opac = float(t.get("opacity", 1.0))
    stroke_w = int(max(0, round(float(t.get("outlineWidth") or 0))))
    stroke_color = (t.get("outline") or "").strip() or None
    fill_color = (t.get("fill") or t.get("color") or "#000000")

    vo = last_v

    # Outline: draw first (below fill)
    if stroke_w > 0 and stroke_color:
        label_border = f"tri_border_{vcount}"
        filters.append(_triangle_clip(label_border, w, h, stroke_color, opac, direction, fps,
                                      inner_offset=max(1, stroke_w), only_border=True))
        vo2 = f"[v{vcount}_tri_b]"
        filters.append(f"{vo}[{label_border}]overlay={x}:{y}:{enable}{vo2}")
        vo = vo2
        vcount += 1

    # Fill: draw inside (shrunk if border exists)
    label_fill = f"tri_fill_{vcount}"
    inner_off = max(1, stroke_w) if (stroke_w > 0 and stroke_color) else 0
    filters.append(_triangle_clip(label_fill, w, h, fill_color, opac, direction, fps,
                                  inner_offset=inner_off, only_border=False))
    vo2 = f"[v{vcount}_tri_f]"
    filters.append(f"{vo}[{label_fill}]overlay={x}:{y}:{enable}{vo2}")
    vo = vo2
    vcount += 1

    return filters, vo, vcount


# ---------- Rectangle helpers (vector, rounded corners) ----------

def _rr_inside_expr(w: int, h: int, r: int) -> str:
    """
    Return a 0/1 expression for a rounded-rectangle of size w×h with corner radius r.
    Uses numeric boolean algebra compatible with geq.
    """
    # Clamp radius at generation time, but also guard here with min(w,h)/2
    r = max(0, min(r, min(w, h) // 2))
    # Basic axis tests
    in_x_mid = f"(gte(X,{r})*lte(X,{w - r}))"
    in_y_mid = f"(gte(Y,0)*lte(Y,{h}))"
    in_y_mid2 = f"(gte(Y,{r})*lte(Y,{h - r}))"
    in_x_full = f"(gte(X,0)*lte(X,{w}))"

    # Centers of corner arcs
    # TL (r,r), TR (w-r,r), BL (r,h-r), BR (w-r,h-r)
    tl = f"lte((X-{r})*(X-{r})+(Y-{r})*(Y-{r}),{r*r})"
    tr = f"lte((X-{w - r})*(X-{w - r})+(Y-{r})*(Y-{r}),{r*r})"
    bl = f"lte((X-{r})*(X-{r})+(Y-{h - r})*(Y-{h - r}),{r*r})"
    br = f"lte((X-{w - r})*(X-{w - r})+(Y-{h - r})*(Y-{h - r}),{r*r})"

    # Inside if within the middle bands OR inside any corner circle
    # OR implemented via sum > 0
    term1 = f"({in_x_mid}*{in_y_mid})"
    term2 = f"({in_y_mid2}*{in_x_full})"
    term_corners = f"({tl}+{tr}+{bl}+{br})"
    return f"gt({term1}+{term2}+{term_corners},0)"


def _rectangle_clip(label: str, w: int, h: int, color: str, alpha: float, fps: int,
                    radius: int = 0, inner_offset: int = 0, only_border: bool = False) -> str:
    """
    Create a w×h RGBA clip with a filled rounded-rectangle (or border) using geq alpha mask.
    If only_border=True, alpha=255 where inside(outer) && !inside(inner).
    inner_offset shrinks width/height and radius for inner mask.
    """
    col = _ff_color(color, alpha)
    R = max(0, int(radius))
    w_in = max(1, w - 2 * max(0, inner_offset))
    h_in = max(1, h - 2 * max(0, inner_offset))
    # Inner radius reduced but not negative
    R_in = max(0, min(R - max(0, inner_offset), min(w_in, h_in) // 2))

    inside_outer = _rr_inside_expr(w, h, R)            # 0/1
    inside_inner = _rr_inside_expr(w_in, h_in, R_in)    # 0/1

    if only_border and inner_offset > 0:
        # Build inner mask in the SAME coordinates: we generated a smaller clip,
        # so we center it by cropping equations via translating X,Y.
        # Simpler approach: create inner mask on separate clip then overlay.
        # But here we emulate border by evaluating inner mask at shifted coords:
        # Shift = inner_offset on X and Y.
        # Replace X->(X-inner_offset), Y->(Y-inner_offset) in inner expression:
        inner_shifted = inside_inner.replace("X", f"(X-{inner_offset})").replace("Y", f"(Y-{inner_offset})")
        mask = f"(({inside_outer})*(1-({inner_shifted})))"
    else:
        # fill = inner (with shift if we applied offset)
        if inner_offset > 0:
            inner_shifted = inside_inner.replace("X", f"(X-{inner_offset})").replace("Y", f"(Y-{inner_offset})")
            mask = f"({inner_shifted})"
        else:
            mask = f"({inside_outer})"

    a_expr = f"if({mask},255,0)"

    return (
        f"color=c={col}:s={w}x{h}:r={fps},format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{a_expr}'[{label}]"
    )


def _emit_rectangle_overlays(t: dict, last_v: str, vcount: int, fps: int):
    """
    Draw stroke (optional) then fill rounded-rectangle at (x,y) with size (width,height).
    """
    filters = []
    x = int(round(float(t.get("x", 0))))
    y = int(round(float(t.get("y", 0))))
    w = int(max(1, round(float(t.get("width", 100)))))
    h = int(max(1, round(float(t.get("height", 100)))))
    radius = int(max(0, round(float(t.get("borderRadius") or 0))))
    enable = f"enable='between(t,{t['start']},{t['end']})'"
    opac = float(t.get("opacity", 1.0))
    stroke_w = int(max(0, round(float(t.get("outlineWidth") or 0))))
    stroke_color = (t.get("outline") or "").strip() or None
    fill_color = (t.get("fill") or t.get("color") or "#000000")

    vo = last_v

    # Outline first (below fill)
    if stroke_w > 0 and stroke_color:
        label_border = f"rect_border_{vcount}"
        filters.append(
            _rectangle_clip(
                label_border, w, h, stroke_color, opac, fps,
                radius=radius, inner_offset=max(1, stroke_w), only_border=True
            )
        )
        vo2 = f"[v{vcount}_rect_b]"
        filters.append(f"{vo}[{label_border}]overlay={x}:{y}:{enable}{vo2}")
        vo = vo2
        vcount += 1

    # Fill (shrunk if border exists)
    label_fill = f"rect_fill_{vcount}"
    inner_off = max(1, stroke_w) if (stroke_w > 0 and stroke_color) else 0
    filters.append(
        _rectangle_clip(
            label_fill, w, h, fill_color, opac, fps,
            radius=radius, inner_offset=inner_off, only_border=False
        )
    )
    vo2 = f"[v{vcount}_rect_f]"
    filters.append(f"{vo}[{label_fill}]overlay={x}:{y}:{enable}{vo2}")
    vo = vo2
    vcount += 1

    return filters, vo, vcount


# ---------- Main entry ----------

def build_ffmpeg_cmd(tl: dict, output_path: str) -> list[str]:
    W, H = int(tl["width"]), int(tl["height"])
    FPS = int(tl["fps"])
    D = float(tl["duration"])
    tracks = sorted(tl["tracks"], key=lambda t: t["z"])
    bg_color = tl.get("background") or "#000000"

    # Optional background image support
    bg_image = tl.get("backgroundImage") or None
    bg_opacity = float(tl.get("backgroundOpacity") if tl.get("backgroundOpacity") is not None else 1.0)
    bg_fit = tl.get("backgroundFit") or "cover"

    # Inputs
    input_flags: list[list[str]] = []
    input_srcs: list[str] = []

    bg_img_input_idx = None
    if bg_image:
        input_flags.append(["-loop", "1", "-t", f"{D}"])
        input_srcs.append(str(bg_image))
        bg_img_input_idx = 0

    for t in tracks:
        typ = t.get("type")
        if typ == "image":
            input_flags.append(["-loop", "1", "-t", f"{D}"])
            input_srcs.append(str(t["src"]))
            t["_in_idx"] = len(input_srcs) - 1
        elif typ in ("video", "audio"):
            input_flags.append([])
            input_srcs.append(str(t["src"]))
            t["_in_idx"] = len(input_srcs) - 1
        # text/circle/triangle/rectangle have no inputs

    # Filters
    filters = []
    filters += _bg_filters(W, H, FPS, bg_color)
    last_v = "[base]"
    vcount = 0

    bg_filters, last_v = _bg_image_filters(bg_img_input_idx, last_v, W, H, bg_fit, bg_opacity)
    filters += bg_filters

    media_filters, last_v, vcount, audio_labels = _media_filters(tracks, last_v, vcount)
    filters += media_filters

    # Text overlays
    for t in tracks:
        if t.get("type") in ("text", "datetime"):
            txt_filters, last_v, vcount = _emit_text_overlay(t, last_v, vcount)
            filters += txt_filters

    # Vector circles
    for t in tracks:
        if t.get("type") == "circle":
            circ_filters, last_v, vcount = _emit_circle_overlays(t, last_v, vcount, FPS)
            filters += circ_filters

    # Vector triangles
    for t in tracks:
        if t.get("type") == "triangle":
            tri_filters, last_v, vcount = _emit_triangle_overlays(t, last_v, vcount, FPS)
            filters += tri_filters

    # Vector rectangles (rounded)
    for t in tracks:
        if t.get("type") == "rectangle":
            rect_filters, last_v, vcount = _emit_rectangle_overlays(t, last_v, vcount, FPS)
            filters += rect_filters

    # Audio mix
    a_filters, afinal = _audio_mix_filters(audio_labels)
    filters += a_filters

    filter_complex = ";".join(filters)

    # Args
    args: list[str] = []
    for flags, src in zip(input_flags, input_srcs):
        args += flags + ["-i", src]

    args += [
        "-filter_complex", filter_complex,
        "-map", last_v,
        "-map", afinal,
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-t", f"{D}",
        "-shortest",
        "-y", output_path,
    ]
    return args
