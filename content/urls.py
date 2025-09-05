# content/urls.py
from django.urls import path
from .views_videos import (
    VideoUploadView, VideoFetchView,
    MyVideoListView, MyVideoDetailView,
)
from .views_images import (
    ImageUploadView, ImageFetchView,
    MyImageListView, MyImageDetailView,
)
from .views_warnings import (
    WarningUploadView, WarningFetchView,
    MyWarningListView, MyWarningDetailView
)


urlpatterns = [
    # keep the same paths your frontend already uses:
    path("videos/upload",  VideoUploadView.as_view(),  name="video-upload-noslash"),
    path("videos/upload/", VideoUploadView.as_view(),  name="video-upload"),
    path("videos/fetch",   VideoFetchView.as_view(),   name="video-fetch-noslash"),
    path("videos/fetch/",  VideoFetchView.as_view(),   name="video-fetch"),
    path("videos/list",    MyVideoListView.as_view(),  name="video-list-noslash"),
    path("videos/list/",   MyVideoListView.as_view(),  name="video-list"),
    path("videos/<int:pk>",  MyVideoDetailView.as_view(), name="video-detail-noslash"),
    path("videos/<int:pk>/", MyVideoDetailView.as_view(), name="video-detail"),
    path("images/upload", ImageUploadView.as_view(), name="image-upload-noslash"),
    path("images/upload/", ImageUploadView.as_view(), name="image-upload"),
    path("images/fetch", ImageFetchView.as_view(), name="image-fetch-noslash"),
    path("images/fetch/", ImageFetchView.as_view(), name="image-fetch"),
    path("images/list", MyImageListView.as_view(), name="image-list-noslash"),
    path("images/list/", MyImageListView.as_view(), name="image-list"),
    path("images/<int:pk>", MyImageDetailView.as_view(), name="image-detail-noslash"),
    path("images/<int:pk>/", MyImageDetailView.as_view(), name="image-detail"),
    path("warnings/upload", WarningUploadView.as_view(), name="warning-upload-noslash"),
    path("warnings/upload/", WarningUploadView.as_view(), name="warning-upload"),
    path("warnings/fetch", WarningFetchView.as_view(), name="warning-fetch-noslash"),
    path("warnings/fetch/", WarningFetchView.as_view(), name="warning-fetch"),
    path("warnings/list", MyWarningListView.as_view(), name="warning-list-noslash"),
    path("warnings/list/", MyWarningListView.as_view(), name="warning-list"),
    path("warnings/<int:pk>", MyWarningDetailView.as_view(), name="warning-detail-noslash"),
    path("warnings/<int:pk>/", MyWarningDetailView.as_view(), name="warning-detail"),
]
