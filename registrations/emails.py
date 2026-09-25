"""Sending the welcome email that contains the (private) WhatsApp invite link."""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import SiteSettings

logger = logging.getLogger(__name__)

WELCOME_SUBJECT = "Welcome to App Fee Waiver — Join the WhatsApp Community"
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class EmailDeliveryError(Exception):
    pass


def send_email(to_email, to_name, subject, html, text):
    """Send one email with the configured provider. Raises EmailDeliveryError on failure."""
    provider = settings.EMAIL_PROVIDER
    if provider == "brevo":
        if not settings.BREVO_API_KEY:
            raise EmailDeliveryError("BREVO_API_KEY is not set.")
        sender_name, sender_email = parseaddr(settings.DEFAULT_FROM_EMAIL)
        payload = {
            "sender": {"name": sender_name or "App Fee Waiver", "email": sender_email},
            "to": [{"email": to_email, "name": to_name[:70]}],
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
        }
        request = urllib.request.Request(
            BREVO_URL,
            data=json.dumps(payload).encode(),
            headers={
                "api-key": settings.BREVO_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status >= 300:
                    raise EmailDeliveryError(f"Brevo returned HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="ignore")[:200]
            raise EmailDeliveryError(f"Brevo HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise EmailDeliveryError(f"Could not reach Brevo: {exc}") from exc
        return

    try:
        message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
    except Exception as exc:  # SMTP/console errors of any kind
        raise EmailDeliveryError(str(exc)) from exc


def send_welcome_email(registration):
    """
    Email the invite link of the registration's WhatsApp group.
    Records success/failure on the registration. Returns True if sent.
    """
    registration.email_attempts += 1
    group = registration.whatsapp_group
    if group is None:
        registration.whatsapp_link_sent = False
        registration.email_error = "No active WhatsApp group available. Add or activate one in Admin, then resend."
        registration.save(update_fields=["email_attempts", "whatsapp_link_sent", "email_error"])
        return False

    site = SiteSettings.load()
    context = {"registration": registration, "invite_link": group.invite_link, "site": site}
    html = render_to_string("emails/welcome.html", context)
    text = render_to_string("emails/welcome.txt", context)
    try:
        send_email(registration.email, registration.full_name, WELCOME_SUBJECT, html, text)
    except EmailDeliveryError as exc:
        logger.warning("Welcome email to registration %s failed: %s", registration.pk, exc)
        registration.whatsapp_link_sent = False
        registration.email_error = str(exc)[:300]
        registration.save(update_fields=["email_attempts", "whatsapp_link_sent", "email_error"])
        return False

    registration.whatsapp_link_sent = True
    registration.email_sent_at = timezone.now()
    registration.email_error = ""
    registration.save(update_fields=["email_attempts", "whatsapp_link_sent", "email_sent_at", "email_error"])
    return True
