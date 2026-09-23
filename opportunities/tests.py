from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .models import Opportunity, OpportunityType, SavedOpportunity

User = get_user_model()


def make_opportunity(**kwargs):
    defaults = dict(
        title="PhD Application Fee Waiver",
        organization="Example University",
        country="United States",
        opportunity_type=OpportunityType.objects.get(slug="application-fee-waivers"),
        degree_level="phd",
        field_of_study="Computer Science",
        funding_type="fee_waiver",
        deadline=timezone.localdate() + timedelta(days=20),
        description="A waiver",
        official_source_url="https://example.edu/waiver",
    )
    defaults.update(kwargs)
    return Opportunity.objects.create(**defaults)


class OpportunityTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(email="m@example.com", password="pw-strong-941", full_name="Member")
        self.mod = User.objects.create_user(email="mod@example.com", password="pw-strong-941", full_name="Mod")
        self.mod.groups.add(Group.objects.get(name="Moderator"))

    def test_descriptive_slug(self):
        opp = make_opportunity()
        self.assertEqual(opp.slug, "example-university-phd-application-fee-waiver")

    def test_submission_is_community_submitted(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("opportunities:submit"), {
            "title": "Master's Scholarship",
            "organization": "Demo Uni",
            "country": "Germany",
            "opportunity_type": OpportunityType.objects.get(slug="scholarships").pk,
            "degree_level": "masters",
            "field_of_study": "Any field",
            "funding_type": "fully_funded",
            "description": "Great scholarship",
            "official_source_url": "https://example.org/s",
        })
        opp = Opportunity.objects.get(title="Master's Scholarship")
        self.assertRedirects(response, opp.get_absolute_url())
        self.assertEqual(opp.status, Opportunity.Status.SUBMITTED)
        self.assertEqual(opp.posted_by, self.member)

    def test_only_moderators_verify(self):
        opp = make_opportunity(posted_by=self.member)
        url = reverse("opportunities:review", args=[opp.slug])
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(url, {"action": "verify"}).status_code, 403)
        self.client.force_login(self.mod)
        self.client.post(url, {"action": "verify"})
        opp.refresh_from_db()
        self.assertTrue(opp.is_verified)
        self.assertTrue(Notification.objects.filter(recipient=self.member, kind="opp_verified").exists())

    def test_filters_hide_expired_and_rejected(self):
        make_opportunity(title="Open one")
        make_opportunity(title="Old one", deadline=timezone.localdate() - timedelta(days=1))
        make_opportunity(title="Scam one", status=Opportunity.Status.REJECTED)
        response = self.client.get(reverse("opportunities:list"))
        self.assertContains(response, "Open one")
        self.assertNotContains(response, "Old one")
        self.assertNotContains(response, "Scam one")
        response = self.client.get(reverse("opportunities:list"), {"deadline": "expired"})
        self.assertContains(response, "Old one")

    def test_filter_by_degree_and_country(self):
        make_opportunity(title="Germany masters", country="Germany", degree_level="masters")
        make_opportunity(title="US PhD")
        response = self.client.get(reverse("opportunities:list"), {"country": "Germany", "degree": "masters"})
        self.assertContains(response, "Germany masters")
        self.assertNotContains(response, "US PhD")

    def test_save_toggle(self):
        opp = make_opportunity()
        self.client.force_login(self.member)
        url = reverse("opportunities:toggle_save", args=[opp.slug])
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH="fetch").json(), {"active": True})
        self.assertTrue(SavedOpportunity.objects.filter(user=self.member).exists())
        self.assertContains(self.client.get(reverse("accounts:saved")), opp.title)
