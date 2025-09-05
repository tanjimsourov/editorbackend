# ffmpegkit/shapes/ellipse.py
from ..colors import _ff_color

def _ellipse_inside_expr(w: int, h: int) -> str:
    """
    0/1 expression for an axis-aligned ellipse filling a w×h box.
    Center (a,b) = (w/2, h/2). Inside test via integer-friendly form:
      ((X-a)^2) * b^2 + ((Y-b)^2) * a^2 <= (a^2)*(b^2)
    """
    a = w / 2.0
    b = h / 2.0
    a2 = a * a
    b2 = b * b
    rhs = a2 * b2
    # Use floats; ffmpeg geq handles them.
    return (
        f"lte(((X-{a})*(X-{a}))*{b2}+((Y-{b})*(Y-{b}))*{a2},{rhs})"
    )

def _ellipse_clip(label: str, w: int, h: int, color: str, alpha: float, fps: int,
                  inner_offset: int = 0, only_border: bool = False) -> str:
    """
    Create a w×h RGBA clip with a filled ellipse (or border) using geq alpha mask.
    If only_border=True, alpha=255 where inside(outer) && !inside(inner).
    inner_offset shrinks width/height for inner mask by 2*offset.
    """
    col = _ff_color(color, alpha)

    # Outer mask (full w×h)
    inside_outer = _ellipse_inside_expr(w, h)

    # Inner (shrunk) mask if offset>0
    if inner_offset > 0:
        w_in = max(1, w - 2 * inner_offset)
        h_in = max(1, h - 2 * inner_offset)
        # Build inner expression in its own local coords, then shift into outer space by +offset
        inner = _ellipse_inside_expr(w_in, h_in)
        inner_shifted = inner.replace("X", f"(X-{inner_offset})").replace("Y", f"(Y-{inner_offset})")
    else:
        inner_shifted = inside_outer

    if only_border and inner_offset > 0:
        # border = outer && !inner
        mask = f"(({inside_outer})*(1-({inner_shifted})))"
    else:
        # fill = inner (or full outer when no offset)
        mask = f"({inner_shifted})"

    a_expr = f"if({mask},255,0)"

    return (
        f"color=c={col}:s={w}x{h}:r={fps},format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{a_expr}'[{label}]"
    )

def _emit_ellipse_overlays(t: dict, last_v: str, vcount: int, fps: int):
    """
    Draw stroke (optional) then fill ellipse, positioned by top-left (x,y) with size (width,height).
    """
    filters = []
    x = int(round(float(t.get("x", 0))))
    y = int(round(float(t.get("y", 0))))
    w = int(max(1, round(float(t.get("width", 100)))))
    h = int(max(1, round(float(t.get("height", 60)))))
    enable = f"enable='between(t,{t['start']},{t['end']})'"
    opac = float(t.get("opacity", 1.0))
    stroke_w = int(max(0, round(float(t.get("outlineWidth") or 0))))
    stroke_color = (t.get("outline") or "").strip() or None
    fill_color = (t.get("fill") or t.get("color") or "#000000")

    vo = last_v

    # Outline first (below fill)
    if stroke_w > 0 and stroke_color:
        label_border = f"ell_border_{vcount}"
        filters.append(
            _ellipse_clip(
                label_border, w, h, stroke_color, opac, fps,
                inner_offset=max(1, stroke_w), only_border=True
            )
        )
        vo2 = f"[v{vcount}_ell_b]"
        filters.append(f"{vo}[{label_border}]overlay={x}:{y}:{enable}{vo2}")
        vo = vo2
        vcount += 1

    # Fill (shrunk if border exists)
    label_fill = f"ell_fill_{vcount}"
    inner_off = max(1, stroke_w) if (stroke_w > 0 and stroke_color) else 0
    filters.append(
        _ellipse_clip(
            label_fill, w, h, fill_color, opac, fps,
            inner_offset=inner_off, only_border=False
        )
    )
    vo2 = f"[v{vcount}_ell_f]"
    filters.append(f"{vo}[{label_fill}]overlay={x}:{y}:{enable}{vo2}")
    vo = vo2
    vcount += 1

    return filters, vo, vcount
