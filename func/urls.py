from django.urls import path

from func import views

urlpatterns = [
    path('save-video', views.VideoUploadView.as_view(), name='save-video'),
    path("unsplash/search", views.UnsplashSearchAPIView.as_view(), name="unsplash_search"),
    path("ai/text2img/", views.DeepAIText2ImgAPIView.as_view(), name="deepai_text2img"),
    path("proxy/image/", views.ImageProxyAPIView.as_view(), name="image_proxy"),
    path('image/remove-bg', views.BackgroundRemoveAPIView.as_view(), name='remove_bg'),
]
