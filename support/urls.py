from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.expert_support, name="expert_support"),
    path("cv-sop-review/", views.cv_sop_review, name="cv_sop_review"),
    path("appointment/", views.appointment, name="appointment"),
]
