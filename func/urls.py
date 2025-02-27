from django.urls import path

from func import  views

urlpatterns = [
     path('get-all-draft', views.GetAllDraft.as_view(), name="GetAllDraft"),
     path('get-all-save', views.GetAllSaved.as_view(), name="GetAllSave"),
     path('get-single-draft/<int:id>/', views.GetSingleDraft.as_view(), name="GetSingleDraft"),
     path('get-single-save/<int:id>/', views.GetSingleSave.as_view(), name="GetSingleDraft"),
     path('add-save', views.AddSaved.as_view(), name="AddSave"),
     path('add-draft', views.AddDraft.as_view(), name="AddDraft"),
     path('get-files', views.FTPFileDataAPIView.as_view(), name="AddDraft"),

]
