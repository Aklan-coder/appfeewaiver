from django.conf import settings
from django.utils import timezone

from .models import SiteSettings


def site_context(request):
    from registrations.forms import RegistrationForm

    return {
        # Empty form for the "Join the Community" pop-up on every page (views may pass their own).
        "join_form": RegistrationForm(),
        "site": SiteSettings.load(),
        "SITE_URL": settings.SITE_URL,
        "TAILWIND_USE_CDN": settings.TAILWIND_USE_CDN,
        "current_year": timezone.now().year,
    }
