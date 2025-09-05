# # urls.py
# from django.urls import path, re_path
# from .views import (
#     LockedCreateView, LockedListView,
#     LockedSaveImageView, LockedSaveVideoView,
# )
#
# urlpatterns = [
#     path("locked/create", LockedCreateView.as_view()),
#     path("locked/list", LockedListView.as_view()),
#     path("locked/<int:locked_id>/save-image",  LockedSaveImageView.as_view(),  name="locked-save-image-noslash"),
#     path("locked/<int:locked_id>/save-image/", LockedSaveImageView.as_view(),  name="locked-save-image"),
#     path("locked/<int:locked_id>/save-video",  LockedSaveVideoView.as_view(),  name="locked-save-video-noslash"),
#     path("locked/<int:locked_id>/save-video/", LockedSaveVideoView.as_view(),  name="locked-save-video"),
# ]
