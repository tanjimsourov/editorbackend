# content/models.py
from django.conf import settings
from django.db import models


def video_upload_to(instance, filename: str) -> str:
    # MEDIA_ROOT/videos/<user_id>/<filename>
    return f"videos/{instance.owner_id}/{filename}"


class VideoContent(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_contents",
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=video_upload_to)  # /media/videos/<uid>/...
    duration_seconds = models.FloatField(null=True, blank=True)  # optional
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner_id})"

    @property
    def file_url(self) -> str:
        # relative path like /media/videos/1/clip.mp4
        return self.file.url if self.file and hasattr(self.file, "url") else ""


def image_upload_to(instance, filename: str) -> str:
    # MEDIA_ROOT/images/<user_id>/<filename>
    return f"images/{instance.owner_id}/{filename}"


class ImageContent(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_contents",
    )
    name = models.CharField(max_length=255)
    file = models.ImageField(upload_to=image_upload_to)  # /media/images/<uid>/...
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner_id})"

    @property
    def file_url(self) -> str:
        # relative path like /media/images/1/image.png
        return self.file.url if self.file and hasattr(self.file, "url") else ""


def warning_upload_to(instance, filename: str) -> str:
    # MEDIA_ROOT/warnings/<user_id>/<filename>
    return f"warnings/{instance.owner_id}/{filename}"


class WarningContent(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="warning_contents",
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=64, blank=True, default="")
    file = models.ImageField(upload_to=warning_upload_to)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner_id})"

    @property
    def file_url(self) -> str:
        # relative url like /media/warnings/<uid>/<file>
        return self.file.url if self.file and hasattr(self.file, "url") else ""
