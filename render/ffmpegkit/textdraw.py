from .colors import _esc_text, _ff_color, _drawtext_font_opt

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
