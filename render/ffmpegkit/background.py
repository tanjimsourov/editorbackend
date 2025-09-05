from .colors import _ff_color

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
