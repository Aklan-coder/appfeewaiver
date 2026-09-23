from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("success-stories/", views.success_stories, name="success_stories"),
    path("new/", views.post_create, name="post_create"),
    path("comments/<int:pk>/edit/", views.comment_edit, name="comment_edit"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
    path("<slug:slug>/edit/", views.post_edit, name="post_edit"),
    path("<slug:slug>/delete/", views.post_delete, name="post_delete"),
    path("<slug:slug>/comment/", views.comment_create, name="comment_create"),
    path("<slug:slug>/like/", views.toggle_reaction, name="toggle_reaction"),
    path("<slug:slug>/save/", views.toggle_save_post, name="toggle_save"),
]
