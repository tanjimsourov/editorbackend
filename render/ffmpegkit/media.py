from __future__ import annotations

from typing import List, Tuple


def _media_filters(tracks, last_v, vcount):
    """
    Build video/image overlays and (conditionally) audio chains.

    IMPORTANT:
    - Expects each media track to have:
        t["_in_idx"]     -> input index for ffmpeg (set in builder)
        t["_has_audio"]  -> bool, whether this input actually has an audio stream
    - Never references [idx:a] unless _has_audio is True.
    """
    filters: List[str] = []
    audio_labels: List[str] = []

    for t in tracks:
        typ = t.get("type")

        # ---------- VIDEO & IMAGE (video chain) ----------
        if typ in ("video", "image"):
            idx = t["_in_idx"]
            vin = f"[{idx}:v]"
            vs = f"[v{vcount}s]"
            vo = f"[v{vcount}o]"

            # optional source trim for video
            if typ == "video":
                vtrim = "setpts=PTS-STARTPTS"
                if t.get("srcIn") is not None or t.get("srcOut") is not None:
                    si = t.get("srcIn") or 0
                    so = t.get("srcOut")
                    if so is not None and float(so) > float(si):
                        vtrim = f"trim=start={si}:end={so},setpts=PTS-STARTPTS"
            else:
                vtrim = "setpts=PTS-STARTPTS"

            w = int(t["w"])
            h = int(t["h"])
            filters.append(f"{vin}scale={w}:{h},format=rgba,{vtrim}{vs}")

            start = float(t["start"])
            end = float(t["end"])
            enable = f"enable='between(t,{start},{end})'"

            x = int(t.get("x", 0))
            y = int(t.get("y", 0))
            filters.append(f"{last_v}{vs}overlay={x}:{y}:{enable}{vo}")

            last_v = vo
            vcount += 1

        # ---------- AUDIO (audio chain) ----------
        if typ in ("video", "audio"):
            if t.get("_has_audio"):
                idx = t["_in_idx"]
                ain = f"[{idx}:a]"
                ao = f"[a{idx}]"

                # Volume/mute handling
                vol = float(t.get("volume", 1.0))
                muted = bool(t.get("muted", False))
                gain = 0.0 if muted else max(0.0, min(1.0, vol))

                # Optional trim
                atrim = "asetpts=PTS-STARTPTS"
                if t.get("srcIn") is not None or t.get("srcOut") is not None:
                    si = t.get("srcIn") or 0
                    so = t.get("srcOut")
                    if so is not None and float(so) > float(si):
                        atrim = f"atrim=start={si}:end={so},asetpts=PTS-STARTPTS"

                # Align audio start to the track's timeline start
                delay_ms = max(0, int(round(float(t.get("start", 0)) * 1000)))

                a_chain = f"{ain}{atrim},adelay={delay_ms}:all=1"
                if gain != 1.0:
                    a_chain += f",volume={gain:.3f}"
                a_chain += f"{ao}"

                filters.append(a_chain)
                audio_labels.append(ao)
            # else: skip cleanly if the input has no audio stream

    return filters, last_v, vcount, audio_labels
