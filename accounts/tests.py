from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .tokens import email_verification_token

User = get_user_model()


class SignupLoginTests(TestCase):
    def test_signup_creates_user_profile_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"full_name": "Ada Lovelace", "email": "Ada@Example.com", "password": "a-strong-pass-941", "agree": "on"},
        )
        self.assertRedirects(response, reverse("core:home"))
        user = User.objects.get(email="ada@example.com")
        self.assertEqual(user.handle, "ada-lovelace")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(len(mail.outbox), 1)  # verification email

    def test_honeypot_blocks_bots(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"full_name": "Bot", "email": "bot@example.com", "password": "a-strong-pass-941", "agree": "on", "website": "spam"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="bot@example.com").exists())

    def test_login_with_email(self):
        User.objects.create_user(email="m@example.com", password="a-strong-pass-941", full_name="Member")
        response = self.client.post(reverse("accounts:login"), {"username": "M@example.com", "password": "a-strong-pass-941"})
        self.assertRedirects(response, reverse("core:home"))

    def test_verify_email_token_survives_login(self):
        user = User.objects.create_user(email="v@example.com", password="a-strong-pass-941", full_name="Verify Me")
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        token = email_verification_token.make_token(user)
        self.client.login(email="v@example.com", password="a-strong-pass-941")
        self.client.get(reverse("accounts:verify_email", args=[urlsafe_base64_encode(force_bytes(user.pk)), token]))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_public_profile_hides_email(self):
        user = User.objects.create_user(email="private@example.com", password="x-strong-pass-941", full_name="Private Person")
        response = self.client.get(reverse("accounts:profile", args=[user.handle]))
        self.assertContains(response, "Private Person")
        self.assertNotContains(response, "private@example.com")
