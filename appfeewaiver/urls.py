from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import sitemaps

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("registrations.urls")),
    path("testimonies/", include("testimonies.urls")),
    path("", include("content.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("", include("core.urls")),
]

handler404 = "core.views.page_not_found"
