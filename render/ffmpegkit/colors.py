import os
import re

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

    rgb_hex, a = _parse_hex_color(c)
    if not rgb_hex:
        rgb_hex, a = _parse_rgb_func(c)

    if rgb_hex:
        if alpha_override is not None:
            a = max(0.0, min(1.0, float(alpha_override)))
        return f"{rgb_hex}@{a:.3f}" if a is not None else rgb_hex

    if alpha_override is not None:
        a = max(0.0, min(1.0, float(alpha_override)))
        return f"{c}@{a:.3f}"
    return c

def _drawtext_font_opt(t: dict) -> str:
    font_path = t.get("fontPath")
    font_family = t.get("fontFamily") or "Arial"

    if font_path and os.path.isfile(font_path):
        safe_path = font_path.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    win_arial = r"C:\Windows\Fonts\arial.ttf"
    if os.name == "nt" and os.path.isfile(win_arial):
        safe_path = win_arial.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    linux_dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.isfile(linux_dejavu):
        safe_path = linux_dejavu.replace(":", r"\:").replace("'", r"\'")
        return f"fontfile='{safe_path}'"

    return f"font='{font_family}'"
