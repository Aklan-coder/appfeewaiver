from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from community.models import Post, PostCategory
from opportunities.models import Opportunity, OpportunityType
from resources.models import Resource, ResourceCategory

from .models import SiteSettings

User = get_user_model()


class PagesTests(TestCase):
    def test_public_pages_render(self):
        for name in [
            "core:home", "core:about", "core:contact", "core:privacy", "core:terms", "core:guidelines",
            "core:disclaimer", "core:search", "community:feed", "community:success_stories",
            "opportunities:list", "resources:list", "support:expert_support", "support:cv_sop_review",
            "support:appointment", "accounts:login", "accounts:signup",
        ]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_home_shows_configured_member_count_not_10000(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "2,000+")
        self.assertNotContains(response, "10,000")

    def test_sitemap_and_robots(self):
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertContains(self.client.get("/robots.txt"), "Sitemap:")

    def test_dashboard_requires_moderator(self):
        member = User.objects.create_user(email="m@example.com", password="pw-strong-941", full_name="M")
        self.client.force_login(member)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 403)
        admin = User.objects.create_superuser(email="admin@example.com", password="pw-strong-941", full_name="Admin")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)


class SiteSettingsEmailTests(TestCase):
    def test_email_buttons_follow_admin_settings(self):
        settings_obj = SiteSettings.load()
        settings_obj.primary_email = "team@example.org"
        settings_obj.cv_review_email = "cv@example.org"
        settings_obj.save()
        response = self.client.get(reverse("support:cv_sop_review"))
        self.assertContains(response, "mailto:cv@example.org?subject=CV%20Review%20Request")
        self.assertContains(response, "mailto:team@example.org?subject=SOP%20Review%20Request")
        response = self.client.get(reverse("support:appointment"))
        self.assertContains(response, "mailto:team@example.org?subject=Appointment%20Request")


class GlobalSearchTests(TestCase):
    def test_search_labels_content_types(self):
        user = User.objects.create_user(email="s@example.com", password="pw-strong-941", full_name="S")
        Post.objects.create(author=user, category=PostCategory.objects.get(slug="scholarships"), title="Computer Science scholarship advice", body="?")
        Opportunity.objects.create(
            title="Computer Science Scholarship", organization="Uni", country="Germany",
            opportunity_type=OpportunityType.objects.get(slug="scholarships"), degree_level="masters",
            field_of_study="Computer Science", description="x", official_source_url="https://example.org",
        )
        Resource.objects.create(title="Computer Science scholarship guide", category=ResourceCategory.objects.first(), summary="How to")
        response = self.client.get(reverse("core:search"), {"q": "Computer Science scholarship"})
        self.assertContains(response, "COMMUNITY POST")
        self.assertContains(response, "SCHOLARSHIP")
        self.assertContains(response, "RESOURCE")

    def test_us_alias(self):
        Opportunity.objects.create(
            title="PhD Fee Waiver", organization="Uni", country="United States",
            opportunity_type=OpportunityType.objects.get(slug="application-fee-waivers"), degree_level="phd",
            description="x", official_source_url="https://example.org",
        )
        response = self.client.get(reverse("core:search"), {"q": "US application fee waiver"})
        self.assertContains(response, "PhD Fee Waiver")
