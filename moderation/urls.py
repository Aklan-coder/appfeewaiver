from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("", views.queue, name="queue"),
    path("reports/<int:pk>/resolve/", views.resolve_report, name="resolve_report"),
    path("report/post/<slug:slug>/", views.report_post, name="report_post"),
    path("report/comment/<int:pk>/", views.report_comment, name="report_comment"),
    path("remove/post/<slug:slug>/", views.remove_post, name="remove_post"),
    path("remove/comment/<int:pk>/", views.remove_comment, name="remove_comment"),
]
