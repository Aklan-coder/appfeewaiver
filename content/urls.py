from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("blog/", views.post_list, name="blog"),
    path("blog/<slug:slug>/", views.post_detail, name="post"),
    path("resources/", views.resource_list, name="resources"),
]
