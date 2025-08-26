from django.urls import path

from webpage import views

urlpatterns = [

    path("screenshot", views.ScreenshotAPIView.as_view(), name="screenshot_api"),

]
