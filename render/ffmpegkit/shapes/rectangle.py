from ..colors import _ff_color

def _rr_inside_expr(w: int, h: int, r: int) -> str:
    r = max(0, min(r, min(w, h) // 2))
    in_x_mid = f"(gte(X,{r})*lte(X,{w - r}))"
    in_y_mid = f"(gte(Y,0)*lte(Y,{h}))"
    in_y_mid2 = f"(gte(Y,{r})*lte(Y,{h - r}))"
    in_x_full = f"(gte(X,0)*lte(X,{w}))"

    tl = f"lte((X-{r})*(X-{r})+(Y-{r})*(Y-{r}),{r*r})"
    tr = f"lte((X-{w - r})*(X-{w - r})+(Y-{r})*(Y-{r}),{r*r})"
    bl = f"lte((X-{r})*(X-{r})+(Y-{h - r})*(Y-{h - r}),{r*r})"
    br = f"lte((X-{w - r})*(X-{w - r})+(Y-{h - r})*(Y-{h - r}),{r*r})"

    term1 = f"({in_x_mid}*{in_y_mid})"
    term2 = f"({in_y_mid2}*{in_x_full})"
    term_corners = f"({tl}+{tr}+{bl}+{br})"
    return f"gt({term1}+{term2}+{term_corners},0)"

def _rectangle_clip(label: str, w: int, h: int, color: str, alpha: float, fps: int,
                    radius: int = 0, inner_offset: int = 0, only_border: bool = False) -> str:
    col = _ff_color(color, alpha)
    R = max(0, int(radius))
    w_in = max(1, w - 2 * max(0, inner_offset))
    h_in = max(1, h - 2 * max(0, inner_offset))
    R_in = max(0, min(R - max(0, inner_offset), min(w_in, h_in) // 2))

    inside_outer = _rr_inside_expr(w, h, R)
    inside_inner = _rr_inside_expr(w_in, h_in, R_in)

    if only_border and inner_offset > 0:
        inner_shifted = inside_inner.replace("X", f"(X-{inner_offset})").replace("Y", f"(Y-{inner_offset})")
        mask = f"(({inside_outer})*(1-({inner_shifted})))"
    else:
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
