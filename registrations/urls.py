from django.urls import path

from . import views

app_name = "registrations"

urlpatterns = [
    path("join/", views.join, name="join"),
]
