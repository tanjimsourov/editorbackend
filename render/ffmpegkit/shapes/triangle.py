from ..colors import _ff_color

def _tri_vertices(w: int, h: int, direction: str):
    if direction == "down":
        return (0, 0), (w, 0), (w // 2, h)
    if direction == "left":
        return (0, h // 2), (w, 0), (w, h)
    if direction == "right":
        return (0, 0), (w, h // 2), (0, h)
    return (w // 2, 0), (0, h), (w, h)

def _inside_tri_expr(v0, v1, v2):
    v0x, v0y = v0
    v1x, v1y = v1
    v2x, v2y = v2

    s1 = f"((X-{v2x})*({v1y}-{v2y})-(Y-{v2y})*({v1x}-{v2x}))"
    s2 = f"((X-{v0x})*({v2y}-{v0y})-(Y-{v0y})*({v2x}-{v0x}))"
    s3 = f"((X-{v1x})*({v0y}-{v1y})-(Y-{v1y})*({v0x}-{v1x}))"

    pos = f"(gte({s1},0)*gte({s2},0)*gte({s3},0))"
    neg = f"(lte({s1},0)*lte({s2},0)*lte({s3},0))"
    return f"gt({pos}+{neg},0)"

def _triangle_clip(label: str, w: int, h: int, color: str, alpha: float, direction: str, fps: int,
                   inner_offset: int = 0, only_border: bool = False) -> str:
    col = _ff_color(color, alpha)
    v0, v1, v2 = _tri_vertices(w, h, direction)
    if inner_offset > 0:
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

    inside_outer = _inside_tri_expr(v0, v1, v2)
    inside_inner = _inside_tri_expr(vi0, vi1, vi2)

    if only_border and inner_offset > 0:
        mask = f"(({inside_outer})*(1-({inside_inner})))"
    else:
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

    if stroke_w > 0 and stroke_color:
        label_border = f"tri_border_{vcount}"
        filters.append(_triangle_clip(label_border, w, h, stroke_color, opac, direction, fps,
                                      inner_offset=max(1, stroke_w), only_border=True))
        vo2 = f"[v{vcount}_tri_b]"
        filters.append(f"{vo}[{label_border}]overlay={x}:{y}:{enable}{vo2}")
        vo = vo2
        vcount += 1

    label_fill = f"tri_fill_{vcount}"
    inner_off = max(1, stroke_w) if (stroke_w > 0 and stroke_color) else 0
    filters.append(_triangle_clip(label_fill, w, h, fill_color, opac, direction, fps,
                                  inner_offset=inner_off, only_border=False))
    vo2 = f"[v{vcount}_tri_f]"
    filters.append(f"{vo}[{label_fill}]overlay={x}:{y}:{enable}{vo2}")
    vo = vo2
    vcount += 1

    return filters, vo, vcount
