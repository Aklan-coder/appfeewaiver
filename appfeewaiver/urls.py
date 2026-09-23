from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import sitemaps

admin.site.site_header = "App Fee Waiver Administration"
admin.site.site_title = "App Fee Waiver Admin"
admin.site.index_title = "Platform management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("community/", include("community.urls")),
    path("opportunities/", include("opportunities.urls")),
    path("resources/", include("resources.urls")),
    path("support/", include("support.urls")),
    path("notifications/", include("notifications.urls")),
    path("moderation/", include("moderation.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.page_not_found"
