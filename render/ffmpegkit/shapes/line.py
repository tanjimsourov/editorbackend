# ffmpegkit/shapes/line.py
import math
from ..colors import _ff_color

def _emit_line_overlays(t: dict, last_v: str, vcount: int, fps: int):
    """
    Draw a straight line using a rotated thin rectangle:
      - Base clip: length x thickness (filled with color @ opacity)
      - Pad to a 2*length square with the line's LEFT-MIDDLE placed at the center
      - Rotate around center (which equals the line's start anchor)
      - Overlay so the center (start anchor) lands at (x, y)
    """
    filters = []

    x = int(round(float(t.get("x", 0))))                 # start anchor X
    y = int(round(float(t.get("y", 0))))                 # start anchor Y
    L = int(max(1, round(float(t.get("length", 200)))))  # line length (px)
    T = int(max(1, round(float(t.get("thickness", 2))))) # thickness (px)
    deg = float(t.get("rotation", 0.0))
    rad = deg * math.pi / 180.0                          # ffmpeg rotate uses radians
    color = t.get("color") or "#000000"
    alpha = float(t.get("opacity", 1.0))
    enable = f"enable='between(t,{t['start']},{t['end']})'"

    # 1) Solid RGBA bar of size L x T
    colspec = _ff_color(color, alpha)  # supports @alpha
    lb = f"line_body_{vcount}"
    filters.append(
        f"color=c={colspec}:s={L}x{T}:r={fps},format=rgba[{lb}]"
    )

    # 2) Pad to 2L x 2L so that the LEFT-MIDDLE of the bar sits at the center
    #    Pad position: top-left of bar at (L, L - T/2) inside the 2L x 2L canvas.
    lp = f"line_pad_{vcount}"
    pad_x = L
    pad_y = L - (T // 2)
    filters.append(
        f"[{lb}]pad=width={2*L}:height={2*L}:x={pad_x}:y={pad_y}:color=black@0[{lp}]"
    )

    # 3) Rotate around center (which is the desired start anchor)
    lr = f"line_rot_{vcount}"
    filters.append(
        f"[{lp}]rotate={rad}:ow=rotw(iw):oh=roth(ih):c=black@0[{lr}]"
    )

    # 4) Overlay so the CENTER lands at (x, y) => top-left = (x - L, y - L)
    vo = f"[v{vcount}_line]"
    ox = x - L
    oy = y - L
    filters.append(
        f"{last_v}[{lr}]overlay={ox}:{oy}:{enable}{vo}"
    )

    return filters, vo, vcount + 1
