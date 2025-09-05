from ..colors import _ff_color

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
