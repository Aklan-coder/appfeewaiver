from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import SiteSettings
from core.utils import client_ip, rate_limit

from .emails import send_welcome_email
from .forms import RegistrationForm
from .models import CommunityRegistration, WhatsAppGroup

RESEND_COOLDOWN = timedelta(minutes=10)


def _is_fetch(request):
    return request.headers.get("x-requested-with") == "fetch"


def register_or_resend(form_data, ip=None):
    """
    Save a new registration (or find the existing one for this email), make sure it
    has a WhatsApp group, and email the link. Returns the registration.
    """
    now = timezone.now()
    existing = CommunityRegistration.objects.filter(email__iexact=form_data["email"]).first()
    if existing:
        existing.last_requested_at = now
        existing.save(update_fields=["last_requested_at"])
        recently_sent = existing.email_sent_at and now - existing.email_sent_at < RESEND_COOLDOWN
        if not recently_sent:
            if existing.whatsapp_group is None or not existing.whatsapp_group.is_active:
                existing.whatsapp_group = WhatsAppGroup.pick_for_new_registration() or existing.whatsapp_group
                existing.save(update_fields=["whatsapp_group"])
            send_welcome_email(existing)
        return existing

    registration = CommunityRegistration.objects.create(
        full_name=form_data["full_name"],
        email=form_data["email"],
        country=form_data["country"],
        current_level=form_data["current_level"],
        field_of_study=form_data.get("field_of_study", ""),
        whatsapp_group=WhatsAppGroup.pick_for_new_registration(),
        last_requested_at=now,
        ip_address=ip,
    )
    send_welcome_email(registration)
    return registration


@require_http_methods(["GET", "POST"])
@rate_limit("register", limit=6, period=3600)
def join(request):
    if request.method == "GET":
        return redirect("/#join")

    site = SiteSettings.load()
    if not site.registration_enabled:
        message = "Registration is paused at the moment. Please check back soon."
        if _is_fetch(request):
            return JsonResponse({"ok": False, "message": message}, status=403)
        return redirect("/#join")

    form = RegistrationForm(request.POST)
    if not form.is_valid():
        if _is_fetch(request):
            errors = {name: [str(e) for e in errs] for name, errs in form.errors.items() if name != "website"}
            return JsonResponse({"ok": False, "errors": errors}, status=400)
        from core.views import home

        return home(request, registration_form=form)

    register_or_resend(form.cleaned_data, ip=client_ip(request))
    # The response is identical whether the email is new or already registered, and it
    # never contains the WhatsApp link: that only goes to the email inbox.
    if _is_fetch(request):
        return JsonResponse({"ok": True})
    return redirect("/?joined=1#join")
