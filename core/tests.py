from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from registrations.models import CommunityRegistration, WhatsAppGroup
from testimonies.models import Testimony

from .models import SiteSettings


class CacheClearedTestCase(TestCase):
    """Site settings and rate limits live in the cache; start every test clean."""

    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()


class PageTests(CacheClearedTestCase):
    def test_public_pages_render(self):
        for path in ["/", "/testimonies/", "/blog/", "/resources/", "/privacy/", "/robots.txt", "/sitemap.xml"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_old_urls_are_gone(self):
        for path in ["/community/", "/accounts/signup/", "/opportunities/"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_public_admin_signup(self):
        self.assertEqual(self.client.get("/admin/register/").status_code, 302)  # redirected to login
        html = self.client.get("/").content.decode()
        self.assertNotIn("Sign up", html)

    def test_home_content(self):
        response = self.client.get("/")
        for text in ["2,000+", "Join the WhatsApp Community", "Latest Funding Testimonies",
                     "Frequently Asked Questions", "About App Fee Waiver", "appfeewaiver@gmail.com"]:
            self.assertContains(response, text)
        self.assertNotContains(response, "10,000")
        for text in ["Application Fee Waivers", "Scholarship Updates", "Fellowships", "Internships", "Mentorship"]:
            self.assertContains(response, text)
        for removed in ["Having trouble?", "Asking a question?", "Got Funded? Share Your Story"]:
            self.assertNotContains(response, removed)

    def test_settings_drive_the_page(self):
        site = SiteSettings.load()
        site.displayed_member_count = "3,500+"
        site.testimony_form_url = "https://forms.gle/example"
        site.community_free_answer = "Yes, joining is free."
        site.linkedin_url = "https://www.linkedin.com/company/example"
        site.save()
        response = self.client.get("/")
        self.assertContains(response, "3,500+")
        self.assertContains(self.client.get("/testimonies/"), "https://forms.gle/example")
        self.assertContains(response, "Is the community free?")
        self.assertContains(response, "https://www.linkedin.com/company/example")

    def test_free_question_hidden_until_answer_set(self):
        self.assertNotContains(self.client.get("/"), "Is the community free?")

    def test_social_icons_hidden_when_not_configured(self):
        self.assertNotContains(self.client.get("/"), "App Fee Waiver on ")

    def test_registration_paused_message(self):
        site = SiteSettings.load()
        site.registration_enabled = False
        site.save()
        self.assertContains(self.client.get("/"), "paused")


class DashboardTests(CacheClearedTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(email="boss@example.com", password="pw-12345-xyz")
        self.client.force_login(self.user)

    def test_dashboard_stats(self):
        group = WhatsAppGroup.objects.create(name="Group 1", invite_link="https://chat.whatsapp.com/X")
        CommunityRegistration.objects.create(full_name="A", email="a@x.com", country="Ghana", current_level="phd",
                                             whatsapp_group=group, whatsapp_link_sent=True)
        CommunityRegistration.objects.create(full_name="B", email="b@x.com", country="Ghana", current_level="phd",
                                             whatsapp_group=group, whatsapp_link_sent=False)
        Testimony.objects.create(name="P", testimony="x", published=True)
        Testimony.objects.create(name="U", testimony="x", published=False)
        Testimony.objects.create(name="D", testimony="x", published=True, is_demo=True)
        response = self.client.get("/admin/")
        stats = {label: value for label, value, _ in response.context["dashboard_stats"]}
        self.assertEqual(stats["Total Registrations"], 2)
        self.assertEqual(stats["Registrations — Last 7 Days"], 2)
        self.assertEqual(stats["Published Testimonies"], 1)
        self.assertEqual(stats["Unpublished Testimonies"], 1)
        self.assertEqual(stats["Email Delivery Failures"], 1)
        self.assertContains(response, "Group 1")

    def test_admin_pages_load(self):
        for name in ["admin:core_sitesettings_changelist", "admin:registrations_communityregistration_changelist",
                     "admin:registrations_whatsappgroup_changelist", "admin:testimonies_testimony_changelist",
                     "admin:testimonies_synclog_changelist", "admin:accounts_user_changelist"]:
            with self.subTest(name=name):
                self.assertIn(self.client.get(reverse(name)).status_code, (200, 302))


class CommandTests(CacheClearedTestCase):
    def test_demo_data_is_marked_and_removable(self):
        call_command("load_demo_data", "--force", stdout=StringIO())
        self.assertTrue(Testimony.objects.exists())
        self.assertFalse(Testimony.objects.filter(is_demo=False).exists())
        self.assertTrue(all("(Demo)" in t.name for t in Testimony.objects.all()))
        from content.models import Post, Resource

        self.assertTrue(all(p.is_demo and p.title.startswith("Demo") for p in Post.objects.all()))
        self.assertTrue(Resource.objects.filter(is_demo=True).exists())
        call_command("load_demo_data", "--force", stdout=StringIO())  # re-running adds nothing new
        self.assertEqual(Post.objects.count(), 4)
        call_command("remove_demo_data", stdout=StringIO())
        self.assertFalse(Testimony.objects.exists())
        self.assertFalse(Post.objects.exists() or Resource.objects.exists())

    @override_settings(DEBUG=False)
    def test_demo_data_refused_in_production(self):
        with self.assertRaises(CommandError):
            call_command("load_demo_data", stdout=StringIO())

    def test_drop_legacy_tables_lists_only_by_default(self):
        out = StringIO()
        call_command("drop_legacy_tables", stdout=out)
        self.assertIn("--confirm", out.getvalue())
