from ..colors import _ff_color, _drawtext_font_opt, _esc_text
from .rectangle import _rectangle_clip
from .circle import _circle_clip


def _pick(d: dict | None, key: str, default=None):
    if not isinstance(d, dict):
        return default
    v = d.get(key)
    return default if v is None else v


def _anchor_x(expr_w: str, panel_w: int, margin: int, align: str) -> str:
    a = (align or "left").lower()
    if a == "center":
        return f"({panel_w}-{expr_w})/2"
    if a == "right":
        return f"{panel_w}-{expr_w}-{margin}"
    return f"{margin}"


def _get_local_box(layout: dict | None, key: str, panel_w: int, panel_h: int,
                   track_x: int, track_y: int):
    """
    Accept panel-local boxes or screen-space boxes.
    If it looks screen-space (bx/by outside panel), translate by (-track_x, -track_y).
    Return (bx,by,bw,bh) in panel coords, or None if it still doesn't fit.
    """
    if not isinstance(layout, dict) or key not in layout:
        return None
    try:
        bx = float(layout[key]["x"])
        by = float(layout[key]["y"])
        bw = float(layout[key]["width"])
        bh = float(layout[key]["height"])
    except Exception:
        return None
    if bw <= 0 or bh <= 0:
        return None

    # Convert from screen space if needed
    if bx >= panel_w or by >= panel_h:
        bx -= float(track_x)
        by -= float(track_y)

    if bx < 0 or by < 0 or bx + bw > panel_w or by + bh > panel_h:
        return None
    return int(round(bx)), int(round(by)), int(round(bw)), int(round(bh))


def _emit_weather_overlays(t: dict, last_v: str, vcount: int, fps: int):
    """
    Weather card (no external fetch):
      - Rounded background + optional border
      - Optional icon circle
      - Optional location, summary, date, attribution
    `layout` boxes are treated as panel-local; screen-space is auto-converted.
    """
    filters = []

    # geometry / timing
    x = int(round(float(t.get("x", 0))))
    y = int(round(float(t.get("y", 0))))
    w = int(max(1, round(float(t.get("width", 300)))))
    h = int(max(1, round(float(t.get("height", 200)))))
    enable = f"enable='between(t,{t['start']},{t['end']})'"

    # colors / sizes
    cols = t.get("colors") or {}
    col_bg = _pick(cols, "background", None)
    col_txt = _pick(cols, "text", "#000000")
    col_high = _pick(cols, "highlight", col_txt)
    col_icon = _pick(cols, "iconBg", "#DDDDDD")
    col_attr = _pick(cols, "attribution", "#666666")
    col_border = _pick(cols, "border", None)

    fs = t.get("fontSizes") or {}
    fs_location = int(max(10, round(float(fs.get("location") or min(h * 0.18, 28)))))
    fs_summary  = int(max(10, round(float(fs.get("summary")  or min(h * 0.14, 22)))))
    fs_date     = int(max(8,  round(float(fs.get("date")     or min(h * 0.12, 18)))))
    fs_attr     = int(max(8,  round(float(fs.get("attribution") or min(h * 0.10, 14)))))

    icon_size = int(max(1, round(float(t.get("iconSize") or min(h * 0.35, 56)))))

    # toggles
    sc = t.get("showComponents") or {}
    show_location = sc.get("location", True)
    show_summary  = bool(sc.get("summary"))
    show_icon     = bool(sc.get("icon"))
    show_date     = bool(sc.get("date"))
    show_attr     = bool(sc.get("attribution"))

    # alignment & layout
    hAlign = (t.get("horizontalAlign") or "left").lower()
    vAlign = (t.get("verticalAlign") or "top").lower()
    layout = t.get("layout") or {}

    # visuals
    margin = int(max(6, round(h * 0.08)))
    radius = int(round(min(w, h) * 0.08))
    border_w = 1 if col_border else 0

    # base canvas
    base = f"wx_base_{vcount}"
    filters.append(f"color=c=black@0:s={w}x{h}:r={fps},format=rgba[{base}]")
    vo = f"[v{vcount}_wx_0]"
    filters.append(f"[{base}]copy{vo}")
    vcount += 1

    # background
    if col_bg:
        lab_bg = f"wx_bg_{vcount}"
        filters.append(_rectangle_clip(lab_bg, w, h, col_bg, 1.0, fps, radius=radius, inner_offset=0, only_border=False))
        vo2 = f"[v{vcount}_wx_bg]"
        filters.append(f"{vo}[{lab_bg}]overlay=0:0{vo2}")
        vo = vo2
        vcount += 1

    # border
    if border_w > 0:
        lab_bo = f"wx_bo_{vcount}"
        filters.append(_rectangle_clip(lab_bo, w, h, col_border, 1.0, fps, radius=radius, inner_offset=max(1, border_w), only_border=True))
        vo2 = f"[v{vcount}_wx_bo]"
        filters.append(f"{vo}[{lab_bo}]overlay=0:0{vo2}")
        vo = vo2
        vcount += 1

    font_opt = _drawtext_font_opt(t)

    def draw_text(vo_in: str, text: str, size: int, color: str, box_key: str | None,
                  default_y_top: int, label: str, halign: str = "left"):
        nonlocal vcount
        txt = _esc_text(text)
        vo_out = f"[{label}_{vcount}]"
        box = _get_local_box(layout, box_key, w, h, x, y) if box_key else None
        if box:
            bx, by, bw, bh = box
            x_expr = f"{bx} + ( {bw} - text_w )/2"
            y_expr = f"{by} + ( {bh} - text_h )/2"
        else:
            x_expr = _anchor_x("text_w", w, margin, halign)
            y_expr = f"{default_y_top}"
        filters.append(
            f"{vo_in}drawtext={font_opt}:text='{txt}':"
            f"fontsize={size}:fontcolor={_ff_color(color, None)}:"
            f"x={x_expr}:y={y_expr}{vo_out}"
        )
        vcount += 1
        return vo_out

    # icon circle
    if show_icon:
        r = max(1, icon_size // 2)
        d = r * 2
        lab_ic = f"wx_icon_{vcount}"
        filters.append(_circle_clip(lab_ic, d, r, col_icon, 1.0, fps))
        box = _get_local_box(layout, "icon", w, h, x, y)
        if box:
            bx, by, bw, bh = box
            ix = bx + (bw - d) // 2
            iy = by + (bh - d) // 2
        else:
            ix = margin
            iy = (h - d) // 2 if vAlign == "middle" else (h - d - margin if vAlign == "bottom" else margin)
        vo2 = f"[v{vcount}_wx_icon]"
        filters.append(f"{vo}[{lab_ic}]overlay={ix}:{iy}{vo2}")
        vo = vo2
        vcount += 1

    # flow
    y_cursor = margin

    # location
    loc_text = str(t.get("location") or t.get("name") or "").strip()
    if show_location and loc_text:
        vo = draw_text(vo, loc_text, fs_location, col_high, "location", y_cursor, "wx_loc", halign=hAlign)
        y_cursor += fs_location + int(margin * 0.5)

    # summary (from track.summary or track.data.summary)
    summary_text = (t.get("summary") or t.get("data", {}).get("summary") or "").strip()
    if show_summary and summary_text:
        vo = draw_text(vo, summary_text, fs_summary, col_txt, "summary", y_cursor, "wx_sum", halign=hAlign)
        y_cursor += fs_summary + int(margin * 0.4)

    # date
    if bool(sc.get("date")):
        date_color = _pick(cols, "date", col_txt)
        vo2 = f"[v{vcount}_wx_date]"
        box = _get_local_box(layout, "date", w, h, x, y)
        if box:
            bx, by, bw, bh = box
            x_expr = f"{bx} + ( {bw} - text_w )/2"
            y_expr = f"{by} + ( {bh} - text_h )/2"
        else:
            x_expr = _anchor_x("text_w", w, margin, hAlign)
            y_expr = f"{y_cursor}"
        filters.append(
            f"{vo}drawtext={font_opt}:text='%{{localtime\\:%Y-%m-%d}}':"
            f"fontsize={fs_date}:fontcolor={_ff_color(date_color, None)}:"
            f"x={x_expr}:y={y_expr}{vo2}"
        )
        vo = vo2
        vcount += 1
        y_cursor += fs_date + int(margin * 0.3)

    # attribution
    if show_attr:
        attr_text = _esc_text(str(_pick(t, "name", "Weather")).strip() or "Weather")
        vo2 = f"[v{vcount}_wx_attr]"
        box = _get_local_box(layout, "attribution", w, h, x, y)
        if box:
            bx, by, bw, bh = box
            x_expr = f"{bx} + ( {bw} - text_w )/2"
            y_expr = f"{by} + ( {bh} - text_h )/2"
        else:
            x_expr = f"{margin}"
            y_expr = f"{h - fs_attr - margin}"
        filters.append(
            f"{vo}drawtext={font_opt}:text='{attr_text}':"
            f"fontsize={fs_attr}:fontcolor={_ff_color(col_attr, None)}:"
            f"x={x_expr}:y={y_expr}{vo2}"
        )
        vo = vo2
        vcount += 1

    # overall opacity
    overall_opacity = float(t.get("opacity", 1.0))
    overall_opacity = max(0.0, min(1.0, overall_opacity))
    vo_op = f"[v{vcount}_wx_alpha]"
    filters.append(f"{vo}format=rgba,colorchannelmixer=aa={overall_opacity:.3f}{vo_op}")
    vo = vo_op
    vcount += 1

    # overlay onto main
    vo_out = f"[v{vcount}_wx_out]"
    filters.append(f"{last_v}{vo}overlay={x}:{y}:{enable}{vo_out}")
    last_v = vo_out
    vcount += 1

    return filters, last_v, vcount
