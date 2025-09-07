from django.urls import path

from .backgrounds_views import BackgroundUploadView, BackgroundFetchView
from .views import (
    PreviewRenderView,     # video preview (unchanged)
    RenderSaveView,        # video export (unchanged)
    ImagePreviewView,      # NEW image preview
    ImageSaveView,         # NEW image export
    LockedListView,
)

urlpatterns = [
    path("backgrounds/upload/", BackgroundUploadView.as_view(), name="background-upload"),
    path("backgrounds/fetch/", BackgroundFetchView.as_view(), name="background-fetch"),
    path("render/preview", PreviewRenderView.as_view(), name="render-preview"),         # video
    path("render", RenderSaveView.as_view(), name="render-save"),                       # video
    path("render/image/preview", ImagePreviewView.as_view(), name="render-image-preview"),
    path("render/image", ImageSaveView.as_view(), name="render-image"),
    path("locked/list", LockedListView.as_view(), name="locked-list"),
]
