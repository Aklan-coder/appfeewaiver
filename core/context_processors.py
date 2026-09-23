from django.conf import settings
from django.utils import timezone

from .countries import COUNTRIES
from .models import SiteSettings


def site_context(request):
    return {
        "site": SiteSettings.load(),
        "SITE_URL": settings.SITE_URL,
        "TAILWIND_USE_CDN": settings.TAILWIND_USE_CDN,
        "PROFILE_PHOTO_UPLOADS_ENABLED": settings.PROFILE_PHOTO_UPLOADS_ENABLED,
        "REQUIRE_EMAIL_VERIFICATION": settings.REQUIRE_EMAIL_VERIFICATION,
        "current_year": timezone.now().year,
        "COUNTRIES": COUNTRIES,
        # Defaults for the like/save partials; views override these with real values.
        "liked_ids": frozenset(),
        "saved_ids": frozenset(),
        "saved_opportunity_ids": frozenset(),
    }
