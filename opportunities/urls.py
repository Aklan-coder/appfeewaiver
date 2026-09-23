from django.urls import path

from . import views

app_name = "opportunities"

urlpatterns = [
    path("", views.opportunity_list, name="list"),
    path("submit/", views.opportunity_submit, name="submit"),
    path("type/<slug:type_slug>/", views.opportunity_list, name="by_type"),
    path("<slug:slug>/", views.opportunity_detail, name="detail"),
    path("<slug:slug>/save/", views.toggle_save, name="toggle_save"),
    path("<slug:slug>/review/", views.review, name="review"),
]
