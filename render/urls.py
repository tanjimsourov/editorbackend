from django.urls import path
from .views import (
    PreviewRenderView,     # video preview (unchanged)
    RenderSaveView,        # video export (unchanged)
    ImagePreviewView,      # NEW image preview
    ImageSaveView,         # NEW image export
    LockedListView,
)

urlpatterns = [
    path("render/preview", PreviewRenderView.as_view(), name="render-preview"),         # video
    path("render", RenderSaveView.as_view(), name="render-save"),                       # video
    path("render/image/preview", ImagePreviewView.as_view(), name="render-image-preview"),
    path("render/image", ImageSaveView.as_view(), name="render-image"),
    path("locked/list", LockedListView.as_view(), name="locked-list"),
]
