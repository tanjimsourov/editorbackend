# # export/models.py
# from django.conf import settings
# from django.db import models
#
#
# class LockedContent(models.Model):
#     TYPE_CHOICES = (("image", "image"), ("video", "video"))
#     STATUS_CHOICES = (("locked", "locked"), ("saved", "saved"))
#
#     # default AutoField `id` (no UUID to keep first migration super simple)
#
#     # Optional owner; you can backfill later and then make it required in a new migration
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="locked_contents",
#         null=True,
#         blank=True,
#         db_index=True,
#     )
#
#     name = models.CharField(max_length=255, default="", blank=True)
#     type = models.CharField(max_length=10, choices=TYPE_CHOICES)
#     duration_seconds = models.PositiveIntegerField(default=0)
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="locked")
#     file = models.FileField(upload_to="locked/", null=True, blank=True)
#
#     created_at = models.DateTimeField(auto_now_add=True)  # like School
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         indexes = [
#             models.Index(fields=["user", "created_at"]),
#         ]
#
#     def __str__(self):
#         return f"{self.name or self.type} • {self.status}"
