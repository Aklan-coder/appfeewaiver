from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .models import Comment, Post, PostCategory, Reaction

User = get_user_model()


class CommunityTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password="pw-strong-941", full_name="Author One")
        self.other = User.objects.create_user(email="b@example.com", password="pw-strong-941", full_name="Other Two")
        self.category = PostCategory.objects.get(slug="scholarships")
        self.post = Post.objects.create(author=self.author, category=self.category, title="Fully funded Master's Germany", body="Tips please")

    def test_seeded_categories_exist(self):
        self.assertEqual(PostCategory.objects.count(), 13)

    def test_feed_and_detail_render(self):
        self.assertContains(self.client.get(reverse("community:feed")), self.post.title)
        self.assertContains(self.client.get(self.post.get_absolute_url()), "Tips please")

    def test_create_post_requires_login(self):
        response = self.client.get(reverse("community:post_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_member_creates_post(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("community:post_create"),
            {"category": self.category.pk, "title": "Which universities waive PhD fees?", "body": "Looking for a list."},
        )
        post = Post.objects.get(title="Which universities waive PhD fees?")
        self.assertRedirects(response, post.get_absolute_url())
        self.assertEqual(post.slug, "which-universities-waive-phd-fees")

    def test_only_author_can_edit(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("community:post_edit", args=[self.post.slug])).status_code, 404)

    def test_comment_and_reply_notify(self):
        self.client.force_login(self.other)
        self.client.post(reverse("community:comment_create", args=[self.post.slug]), {"body": "Check DAAD."})
        comment = Comment.objects.get(post=self.post)
        self.assertTrue(Notification.objects.filter(recipient=self.author, kind="comment").exists())

        self.client.force_login(self.author)
        self.client.post(reverse("community:comment_create", args=[self.post.slug]), {"body": "Thanks!", "parent_id": comment.pk})
        self.assertTrue(Notification.objects.filter(recipient=self.other, kind="reply").exists())

    def test_like_toggle_json(self):
        self.client.force_login(self.other)
        url = reverse("community:toggle_reaction", args=[self.post.slug])
        data = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertEqual(data, {"active": True, "count": 1})
        data = self.client.post(url, HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertEqual(data, {"active": False, "count": 0})
        self.assertFalse(Reaction.objects.exists())

    def test_filters_and_search(self):
        Post.objects.create(author=self.other, category=self.category, title="Unrelated question", body="Visa help")
        response = self.client.get(reverse("community:feed"), {"q": "Master's Germany"})
        self.assertContains(response, self.post.title)
        self.assertNotContains(response, "Unrelated question")
        response = self.client.get(reverse("community:feed"), {"sort": "unanswered"})
        self.assertContains(response, "Unrelated question")

    def test_suspended_member_cannot_post(self):
        self.other.suspended_until = timezone.now() + timedelta(days=1)
        self.other.save()
        self.client.force_login(self.other)
        self.client.post(reverse("community:comment_create", args=[self.post.slug]), {"body": "Hello"})
        self.assertFalse(Comment.objects.exists())

    def test_removed_post_hidden(self):
        self.post.status = Post.Status.REMOVED
        self.post.save()
        self.assertEqual(self.client.get(self.post.get_absolute_url()).status_code, 404)
