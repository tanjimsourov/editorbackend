def _audio_mix_filters(audio_labels):
    if len(audio_labels) == 0:
        return ["anullsrc=channel_layout=stereo:sample_rate=48000[aout]"], "[aout]"
    if len(audio_labels) == 1:
        return [], audio_labels[0]
    return ["".join(audio_labels) + f"amix=inputs={len(audio_labels)}:normalize=1[aout]"], "[aout]"
