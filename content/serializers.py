# content/serializers.py
from rest_framework import serializers
from .models import VideoContent, ImageContent


class VideoContentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoContent
        fields = ["id", "name", "file_url", "duration_seconds", "created_at"]

    def get_file_url(self, obj: VideoContent) -> str:
        request = self.context.get("request")
        url = obj.file_url
        return request.build_absolute_uri(url) if (request and url and url.startswith("/")) else url


class ImageContentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()  # relative path explicitly exposed

    class Meta:
        model = ImageContent
        fields = ["id", "name", "url", "file_url", "width", "height", "created_at"]

    def get_file_url(self, obj: ImageContent) -> str:
        request = self.context.get("request")
        url = obj.file_url
        return request.build_absolute_uri(url) if (request and url and url.startswith("/")) else url

    def get_url(self, obj: ImageContent) -> str:
        # relative path for your canvas/store (e.g. "/media/images/1/img-uuid.png")
        return obj.file_url

from .models import WarningContent

class WarningContentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = WarningContent
        fields = ["id", "name", "category", "url", "file_url", "width", "height", "created_at"]

    def get_file_url(self, obj: WarningContent) -> str:
        request = self.context.get("request")
        url = obj.file_url
        return request.build_absolute_uri(url) if (request and url and url.startswith("/")) else url

    def get_url(self, obj: WarningContent) -> str:
        # relative path for frontend/canvas
        return obj.file_url