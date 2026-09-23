from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from community.models import Post, PostCategory

from .models import Report

User = get_user_model()


class ModerationTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password="pw-strong-941", full_name="Author")
        self.reporter = User.objects.create_user(email="r@example.com", password="pw-strong-941", full_name="Reporter")
        self.mod = User.objects.create_user(email="mod@example.com", password="pw-strong-941", full_name="Mod")
        self.mod.groups.add(Group.objects.get(name="Moderator"))
        self.post = Post.objects.create(
            author=self.author, category=PostCategory.objects.first(), title="Pay me for a scholarship", body="Send money"
        )

    def test_report_and_remove_with_suspension(self):
        self.client.force_login(self.reporter)
        self.client.post(reverse("moderation:report_post", args=[self.post.slug]), {"reason": "scam"})
        report = Report.objects.get()
        # A second report from the same member is not duplicated
        self.client.post(reverse("moderation:report_post", args=[self.post.slug]), {"reason": "spam"})
        self.assertEqual(Report.objects.count(), 1)

        self.assertEqual(self.client.get(reverse("moderation:queue")).status_code, 403)
        self.client.force_login(self.mod)
        self.assertContains(self.client.get(reverse("moderation:queue")), self.post.title)
        self.client.post(reverse("moderation:resolve_report", args=[report.pk]), {"action": "remove_suspend", "note": "Scam"})
        self.post.refresh_from_db()
        self.author.refresh_from_db()
        self.assertEqual(self.post.status, Post.Status.REMOVED)
        self.assertTrue(self.author.is_suspended)
        self.assertEqual(self.author.warning_count, 1)
