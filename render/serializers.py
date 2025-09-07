from rest_framework import serializers


class BaseTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(
        choices=[
            "video",
            "audio",
            "image",
            "text",
            "datetime",
            "circle",
            "triangle",
            "rectangle",
            "line",
            "ellipse",
            "sign",
            "weather",
        ]
    )
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()
    enable = serializers.BooleanField(required=False)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


class PositionedSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()
    w = serializers.FloatField(required=False, default=0)
    h = serializers.FloatField(required=False, default=0)
    rotation = serializers.FloatField(required=False, default=0)
    opacity = serializers.FloatField(required=False, default=1)


class VideoTrackSerializer(BaseTrackSerializer, PositionedSerializer):
    src = serializers.CharField()
    volume = serializers.FloatField(required=False, min_value=0, max_value=1, default=1)
    muted = serializers.BooleanField(required=False, default=False)
    playbackRate = serializers.FloatField(required=False, default=1.0)
    srcIn = serializers.FloatField(required=False, min_value=0)
    srcOut = serializers.FloatField(required=False, min_value=0)


class ImageTrackSerializer(BaseTrackSerializer, PositionedSerializer):
    src = serializers.CharField()


class TextLikeSerializer(BaseTrackSerializer, PositionedSerializer):
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fontFamily = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fontPath = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fontSize = serializers.IntegerField(required=False, default=48)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    align = serializers.ChoiceField(required=False, choices=["left", "center", "right"], default="left")
    strokeColor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    strokeWidth = serializers.FloatField(required=False, default=0)
    shadowColor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    shadowBlur = serializers.FloatField(required=False, default=0)
    bgColor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    padding = serializers.IntegerField(required=False, default=6)


class TextTrackSerializer(TextLikeSerializer):
    pass


class DateTimeTrackSerializer(TextLikeSerializer):
    isLive = serializers.BooleanField(required=False, default=False)
    useUTC = serializers.BooleanField(required=False, default=False)
    ffFormat = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    offsetDays = serializers.FloatField(required=False, default=0.0)


class AudioTrackSerializer(BaseTrackSerializer):
    src = serializers.CharField()
    volume = serializers.FloatField(required=False, min_value=0, max_value=1, default=1)
    gainDb = serializers.FloatField(required=False, default=0)
    srcIn = serializers.FloatField(required=False, min_value=0)
    srcOut = serializers.FloatField(required=False, min_value=0)


# Circle
class CircleTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["circle"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()  # center X
    y = serializers.FloatField()  # center Y
    radius = serializers.FloatField(min_value=0.5)
    fill = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outlineWidth = serializers.FloatField(required=False, default=0)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# Triangle
class TriangleTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["triangle"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)

    fill = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # fallback
    outline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outlineWidth = serializers.FloatField(required=False, default=0)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)
    direction = serializers.ChoiceField(required=False, choices=["up", "down", "left", "right"], default="up")

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# Rectangle
class RectangleTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["rectangle"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)

    fill = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outlineWidth = serializers.FloatField(required=False, default=0)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)
    borderRadius = serializers.FloatField(required=False, min_value=0.0, default=0.0)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# Line
class LineTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["line"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    length = serializers.FloatField(min_value=1)
    rotation = serializers.FloatField()
    color = serializers.CharField()
    thickness = serializers.FloatField(min_value=1)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# Ellipse
class EllipseTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["ellipse"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)

    fill = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    color = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    outlineWidth = serializers.FloatField(required=False, default=0)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# Sign (composite vector) – unchanged
class _ShowComponentsSerializer(serializers.Serializer):
    text = serializers.BooleanField(required=False, default=False)
    icon = serializers.BooleanField(required=False, default=False)
    arrow = serializers.BooleanField(required=False, default=False)
    symbol = serializers.BooleanField(required=False, default=False)
    background = serializers.BooleanField(required=False, default=False)
    border = serializers.BooleanField(required=False, default=False)


class _ColorsSerializer(serializers.Serializer):
    background = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    highlight = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    border = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    icon = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    arrow = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    symbol = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class _FontSizesSerializer(serializers.Serializer):
    text = serializers.IntegerField(required=False, min_value=1)
    symbol = serializers.IntegerField(required=False, min_value=1)


class _ImageSettingsSerializer(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    width = serializers.IntegerField(required=False, min_value=1)
    height = serializers.IntegerField(required=False, min_value=1)
    borderRadius = serializers.IntegerField(required=False, min_value=0)
    borderWidth = serializers.IntegerField(required=False, min_value=0)
    borderColor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    maintainAspectRatio = serializers.BooleanField(required=False, default=True)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)


class SignTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["sign"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)
    rotation = serializers.FloatField(required=False, default=0.0)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)

    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    symbolType = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    customSymbol = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    showComponents = _ShowComponentsSerializer(required=False)
    colors = _ColorsSerializer(required=False)
    fontSizes = _FontSizesSerializer(required=False)

    iconSize = serializers.IntegerField(required=False, min_value=1)
    image = _ImageSettingsSerializer(required=False)

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


# -------- Weather track --------

class _WxShowComponentsSerializer(serializers.Serializer):
    summary = serializers.BooleanField(required=False, default=False)
    temperature = serializers.BooleanField(required=False, default=False)
    maxTemp = serializers.BooleanField(required=False, default=False)
    minTemp = serializers.BooleanField(required=False, default=False)
    humidity = serializers.BooleanField(required=False, default=False)
    windSpeed = serializers.BooleanField(required=False, default=False)
    windDirection = serializers.BooleanField(required=False, default=False)
    icon = serializers.BooleanField(required=False, default=False)
    date = serializers.BooleanField(required=False, default=False)
    attribution = serializers.BooleanField(required=False, default=False)
    image = serializers.BooleanField(required=False, default=False)
    location = serializers.BooleanField(required=False, default=True)  # allow toggle


class _WxColorsSerializer(serializers.Serializer):
    background = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    highlight = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    border = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    temperature = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    maxTemp = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    minTemp = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    humidity = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    windSpeed = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    windDirection = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    iconBg = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attribution = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    imageBorder = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class _WxFontSizesSerializer(serializers.Serializer):
    location = serializers.IntegerField(required=False, min_value=1)
    summary = serializers.IntegerField(required=False, min_value=1)
    temperature = serializers.IntegerField(required=False, min_value=1)
    maxTemp = serializers.IntegerField(required=False, min_value=1)
    minTemp = serializers.IntegerField(required=False, min_value=1)
    humidity = serializers.IntegerField(required=False, min_value=1)
    windSpeed = serializers.IntegerField(required=False, min_value=1)
    windDirection = serializers.IntegerField(required=False, min_value=1)
    date = serializers.IntegerField(required=False, min_value=1)
    attribution = serializers.IntegerField(required=False, min_value=1)


class _WxImageSerializer(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    width = serializers.IntegerField(required=False, min_value=1)
    height = serializers.IntegerField(required=False, min_value=1)
    borderRadius = serializers.IntegerField(required=False, min_value=0)
    borderWidth = serializers.IntegerField(required=False, min_value=0)
    borderColor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    maintainAspectRatio = serializers.BooleanField(required=False, default=True)
    opacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)


class _WxLayoutItemSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)


class _WxDataSerializer(serializers.Serializer):
    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    icon = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # e.g., "01d"
    temperature = serializers.FloatField(required=False)
    maxTemp = serializers.FloatField(required=False)
    minTemp = serializers.FloatField(required=False)
    humidity = serializers.FloatField(required=False)
    windSpeed = serializers.FloatField(required=False)
    windDirection = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # deg or text
    dateText = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attributionText = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class WeatherTrackSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=["weather"])
    start = serializers.FloatField(min_value=0)
    end = serializers.FloatField(min_value=0)
    z = serializers.IntegerField()

    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField(min_value=1)
    height = serializers.FloatField(min_value=1)

    location = serializers.CharField(required=False, allow_blank=True, default="")
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)
    units = serializers.ChoiceField(required=False, choices=["metric", "imperial"], default="metric")
    language = serializers.CharField(required=False, default="en")
    showDaytimeOnly = serializers.BooleanField(required=False, default=False)
    horizontalAlign = serializers.ChoiceField(required=False, choices=["left", "center", "right"], default="left")
    verticalAlign = serializers.ChoiceField(required=False, choices=["top", "middle", "bottom"], default="top")

    showComponents = _WxShowComponentsSerializer(required=False)
    colors = _WxColorsSerializer(required=False)
    fontSizes = _WxFontSizesSerializer(required=False)
    iconSize = serializers.IntegerField(required=False, min_value=1, default=48)
    image = _WxImageSerializer(required=False)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    layout = serializers.DictField(child=_WxLayoutItemSerializer(), required=False)
    data = _WxDataSerializer(required=False)  # 👈 NOW ACCEPTED

    def validate(self, data):
        if data["end"] < data["start"]:
            raise serializers.ValidationError("Track end must be >= start.")
        return data


class TimelineSerializer(serializers.Serializer):
    duration = serializers.FloatField(min_value=0.0, required=False, default=0.0)
    width = serializers.IntegerField(min_value=16)
    height = serializers.IntegerField(min_value=16)
    fps = serializers.IntegerField(min_value=1, required=False, default=30)

    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    background = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    backgroundImage = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    backgroundOpacity = serializers.FloatField(required=False, min_value=0.0, max_value=1.0, default=1.0)
    backgroundFit = serializers.ChoiceField(required=False, choices=["cover", "contain", "stretch"], default="cover")

    tracks = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    meta = serializers.DictField(required=False)

    def validate(self, data):
        typed_tracks = []
        for tr in data.get("tracks", []):
            t = tr.get("type")
            if t == "video":
                s = VideoTrackSerializer(data=tr)
            elif t == "image":
                s = ImageTrackSerializer(data=tr)
            elif t == "text":
                s = TextTrackSerializer(data=tr)
            elif t == "datetime":
                s = DateTimeTrackSerializer(data=tr)
            elif t == "audio":
                s = AudioTrackSerializer(data=tr)
            elif t == "circle":
                s = CircleTrackSerializer(data=tr)
            elif t == "triangle":
                s = TriangleTrackSerializer(data=tr)
            elif t == "rectangle":
                s = RectangleTrackSerializer(data=tr)
            elif t == "line":
                s = LineTrackSerializer(data=tr)
            elif t == "ellipse":
                s = EllipseTrackSerializer(data=tr)
            elif t == "sign":
                s = SignTrackSerializer(data=tr)
            elif t == "weather":
                s = WeatherTrackSerializer(data=tr)
            else:
                raise serializers.ValidationError(f"Unknown track type: {t}")

            s.is_valid(raise_exception=True)
            typed_tracks.append(s.validated_data)

        data["tracks"] = typed_tracks

        dur = float(data.get("duration") or 0.0)
        if dur > 0:
            for tr in typed_tracks:
                if tr["start"] < 0 or tr["end"] < 0:
                    raise serializers.ValidationError("Track times must be non-negative.")
                if tr["start"] > dur or tr["end"] > dur:
                    raise serializers.ValidationError(
                        f"Track '{tr.get('id','')}' exceeds timeline duration ({dur}s)."
                    )

        return data
