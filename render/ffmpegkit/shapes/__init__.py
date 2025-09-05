from .circle import _emit_circle_overlays
from .triangle import _emit_triangle_overlays
from .rectangle import _emit_rectangle_overlays
from .line import _emit_line_overlays
from .ellipse import _emit_ellipse_overlays
from .sign import _emit_sign_overlays
from .weather import _emit_weather_overlays   # ✅ NEW

__all__ = [
    "_emit_circle_overlays",
    "_emit_triangle_overlays",
    "_emit_rectangle_overlays",
    "_emit_line_overlays",
    "_emit_ellipse_overlays",
    "_emit_sign_overlays",
    "_emit_weather_overlays",  # ✅
]
