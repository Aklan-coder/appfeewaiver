from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("community-guidelines/", views.guidelines, name="guidelines"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("search/", views.search, name="search"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
]
