from django.urls import path

from . import views

app_name = "testimonies"

urlpatterns = [
    path("", views.testimony_list, name="list"),
    path("sync/", views.sync_endpoint, name="sync"),
]
