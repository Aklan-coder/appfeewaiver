from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import SiteSettings

from .emails import EmailDeliveryError, send_welcome_email
from .models import CommunityRegistration, WhatsAppGroup

LINK_1 = "https://chat.whatsapp.com/SECRETGROUPONE"
LINK_2 = "https://chat.whatsapp.com/SECRETGROUPTWO"


class CacheClearedTestCase(TestCase):
    """Site settings and rate limits live in the cache; start every test clean."""

    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()


def form_data(**overrides):
    data = {
        "full_name": "Ada Okafor",
        "email": "ada@example.com",
        "country": "Nigeria",
        "current_level": "masters",
        "field_of_study": "Computer Science",
        "website": "",
    }
    data.update(overrides)
    return data


@override_settings(EMAIL_PROVIDER="console")
class RegistrationTests(CacheClearedTestCase):
    def setUp(self):
        cache.clear()
        self.g1 = WhatsAppGroup.objects.create(name="Group 1", invite_link=LINK_1, order=1)
        self.g2 = WhatsAppGroup.objects.create(name="Group 2", invite_link=LINK_2, order=2)
        self.url = reverse("registrations:join")

    def post(self, fetch=True, **overrides):
        headers = {"HTTP_X_REQUESTED_WITH": "fetch"} if fetch else {}
        return self.client.post(self.url, form_data(**overrides), **headers)

    # --- saving & validation -------------------------------------------------
    def test_registration_is_saved_and_email_contains_link(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        reg = CommunityRegistration.objects.get()
        self.assertEqual(reg.full_name, "Ada Okafor")
        self.assertEqual(reg.country, "Nigeria")
        self.assertEqual(reg.whatsapp_group, self.g1)
        self.assertTrue(reg.whatsapp_link_sent)
        self.assertIsNotNone(reg.email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["ada@example.com"])
        self.assertIn("WhatsApp", message.subject)
        self.assertIn(LINK_1, message.body)
        self.assertIn(LINK_1, message.alternatives[0][0])

    def test_link_never_in_response_or_public_pages(self):
        response = self.post()
        self.assertNotIn("chat.whatsapp.com", response.content.decode())
        response = self.post(fetch=False, email="other@example.com")
        self.assertRedirects(response, "/?joined=1#join", fetch_redirect_response=False)
        for path in ["/", "/?joined=1", reverse("testimonies:list"), reverse("core:privacy")]:
            html = self.client.get(path).content.decode()
            self.assertNotIn("chat.whatsapp.com", html, path)
        self.assertNotIn("chat.whatsapp.com", open("static/js/site.js").read())

    def test_success_message_in_page_after_non_js_submit(self):
        self.post(fetch=False)
        html = self.client.get("/?joined=1").content.decode()
        self.assertIn("You're in!", html.replace("&#x27;", "'"))

    def test_validation_errors(self):
        response = self.post(full_name="", email="not-an-email", country="", current_level="")
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertEqual(set(errors), {"full_name", "email", "country", "current_level"})
        self.assertFalse(CommunityRegistration.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_join_popup_closed_by_default_and_open_after_submit(self):
        self.assertNotContains(self.client.get("/"), 'class="join-modal is-open"')
        self.assertContains(self.client.get("/?joined=1"), 'class="join-modal is-open"')

    def test_validation_errors_without_js_rerender_form(self):
        response = self.post(fetch=False, email="bad")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'class="join-modal is-open"', status_code=400)
        self.assertContains(response, "Enter a valid email address", status_code=400)

    def test_field_of_study_optional(self):
        self.post(field_of_study="")
        self.assertEqual(CommunityRegistration.objects.get().field_of_study, "")

    def test_honeypot_blocks_bots(self):
        response = self.post(website="http://spam.example")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CommunityRegistration.objects.exists())

    def test_registration_disabled(self):
        site = SiteSettings.load()
        site.registration_enabled = False
        site.save()
        response = self.post()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CommunityRegistration.objects.exists())

    def test_rate_limit(self):
        for i in range(6):
            self.post(email=f"user{i}@example.com")
        response = self.post(email="user99@example.com")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(CommunityRegistration.objects.count(), 6)

    # --- duplicates -------------------------------------------------------------
    def test_duplicate_email_does_not_create_second_row_and_respects_cooldown(self):
        self.post()
        response = self.post(email="ADA@example.com", full_name="Someone Else")
        self.assertEqual(response.json(), {"ok": True})  # same response: no account enumeration
        self.assertEqual(CommunityRegistration.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # within cooldown: not re-sent

        CommunityRegistration.objects.update(email_sent_at=timezone.now() - timedelta(minutes=11))
        self.post()
        self.assertEqual(CommunityRegistration.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    # --- group assignment -------------------------------------------------------
    def test_balanced_assignment_between_two_groups(self):
        for i in range(6):
            self.post(email=f"s{i}@example.com")
            cache.clear()
        groups = list(CommunityRegistration.objects.order_by("pk").values_list("whatsapp_group__name", flat=True))
        self.assertEqual(groups, ["Group 1", "Group 2"] * 3)

    def test_inactive_group_is_skipped(self):
        self.g1.is_active = False
        self.g1.save()
        for i in range(3):
            self.post(email=f"s{i}@example.com")
        self.assertEqual(set(CommunityRegistration.objects.values_list("whatsapp_group", flat=True)), {self.g2.pk})
        self.assertTrue(all(LINK_2 in m.body for m in mail.outbox))

    def test_full_group_is_skipped(self):
        self.g1.capacity = 1
        self.g1.save()
        for i in range(4):
            self.post(email=f"s{i}@example.com")
        self.assertEqual(self.g1.registrations.count(), 1)
        self.assertEqual(self.g2.registrations.count(), 3)

    def test_third_group_joins_rotation_without_code_changes(self):
        g3 = WhatsAppGroup.objects.create(name="Group 3", invite_link="https://chat.whatsapp.com/THREE", order=3)
        for i in range(3):
            self.post(email=f"s{i}@example.com")
        self.assertEqual(g3.registrations.count(), 1)

    def test_changing_link_affects_next_email(self):
        self.post(email="a@example.com")
        self.g2.delete()
        self.g1.invite_link = "https://chat.whatsapp.com/NEWLINK"
        self.g1.save()
        self.post(email="b@example.com")
        self.assertIn(LINK_1, mail.outbox[0].body)
        self.assertIn("https://chat.whatsapp.com/NEWLINK", mail.outbox[1].body)

    def test_no_active_group_records_error(self):
        WhatsAppGroup.objects.update(is_active=False)
        response = self.post()
        self.assertEqual(response.json(), {"ok": True})
        reg = CommunityRegistration.objects.get()
        self.assertIsNone(reg.whatsapp_group)
        self.assertFalse(reg.whatsapp_link_sent)
        self.assertIn("No active WhatsApp group", reg.email_error)
        self.assertEqual(len(mail.outbox), 0)

    # --- email failures -------------------------------------------------------
    def test_email_failure_is_recorded_and_resend_works(self):
        with mock.patch("registrations.emails.send_email", side_effect=EmailDeliveryError("Brevo HTTP 401")):
            response = self.post()
        self.assertEqual(response.json(), {"ok": True})
        reg = CommunityRegistration.objects.get()
        self.assertFalse(reg.whatsapp_link_sent)
        self.assertIn("401", reg.email_error)
        self.assertEqual(reg.email_attempts, 1)

        self.assertTrue(send_welcome_email(reg))
        reg.refresh_from_db()
        self.assertTrue(reg.whatsapp_link_sent)
        self.assertEqual(reg.email_error, "")
        self.assertEqual(reg.email_attempts, 2)

    @override_settings(EMAIL_PROVIDER="brevo", BREVO_API_KEY="")
    def test_brevo_without_key_fails_cleanly(self):
        self.post()
        reg = CommunityRegistration.objects.get()
        self.assertFalse(reg.whatsapp_link_sent)
        self.assertIn("BREVO_API_KEY", reg.email_error)

    @override_settings(EMAIL_PROVIDER="brevo", BREVO_API_KEY="test-key", DEFAULT_FROM_EMAIL="AFW <hi@example.com>")
    def test_brevo_request_payload(self):
        class FakeResponse:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            self.post()
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.get_header("Api-key"), "test-key")
        self.assertIn(LINK_1, request.data.decode())
        self.assertTrue(CommunityRegistration.objects.get().whatsapp_link_sent)


@override_settings(EMAIL_PROVIDER="console")
class RegistrationAdminTests(CacheClearedTestCase):
    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_superuser(email="boss@example.com", password="pw-12345-xyz")
        self.client.force_login(self.admin)
        self.g1 = WhatsAppGroup.objects.create(name="Group 1", invite_link=LINK_1, order=1)
        self.g2 = WhatsAppGroup.objects.create(name="Group 2", invite_link=LINK_2, order=2)
        self.reg = CommunityRegistration.objects.create(
            full_name="Ada", email="ada@example.com", country="Ghana", current_level="phd", whatsapp_group=self.g1
        )

    def changelist(self):
        return reverse("admin:registrations_communityregistration_changelist")

    def test_changelist_search_and_filters(self):
        self.assertContains(self.client.get(self.changelist(), {"q": "ada"}), "ada@example.com")
        self.assertEqual(self.client.get(self.changelist(), {"country": "Ghana"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:registrations_whatsappgroup_changelist")).status_code, 200)

    def test_resend_action(self):
        response = self.client.post(self.changelist(), {"action": "resend_whatsapp_email", "_selected_action": [self.reg.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(LINK_1, mail.outbox[0].body)

    def test_export_csv(self):
        response = self.client.post(self.changelist(), {"action": "export_csv", "_selected_action": [self.reg.pk]})
        self.assertEqual(response["Content-Type"].split(";")[0], "text/csv")
        self.assertIn("ada@example.com", response.content.decode())

    def test_move_to_group_action(self):
        response = self.client.post(
            self.changelist(), {"action": f"move_to_group_{self.g2.pk}", "_selected_action": [self.reg.pk]}
        )
        self.assertEqual(response.status_code, 302)
        self.reg.refresh_from_db()
        self.assertEqual(self.reg.whatsapp_group, self.g2)
        self.assertIn(LINK_2, mail.outbox[0].body)

    def test_anonymous_cannot_see_admin(self):
        self.client.logout()
        response = self.client.get(self.changelist())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
