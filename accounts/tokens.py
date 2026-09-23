from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token stays valid across logins; becomes invalid once the email is verified."""

    key_salt = "accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()


def send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = settings.SITE_URL + reverse("accounts:verify_email", args=[uid, token])
    body = render_to_string("accounts/emails/verify_email.txt", {"user": user, "link": link})
    send_mail(
        "Confirm your email – App Fee Waiver",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
