from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Post, PostCategory, Resource, ResourceCategory


class ContentTestCase(TestCase):
    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()


class BlogTests(ContentTestCase):
    def setUp(self):
        self.post = Post.objects.create(
            title="Fully Funded Fellowship 2027", slug="fellowship-2027", category=PostCategory.FELLOWSHIP,
            body="First paragraph.\n\nApply at https://example.org/apply", deadline=timezone.now().date(),
        )
        self.draft = Post.objects.create(title="Secret draft", slug="draft", body="x", published=False)
        self.future = Post.objects.create(
            title="Scheduled post", slug="later", body="x", published_at=timezone.now() + timedelta(days=2)
        )

    def test_list_shows_only_published(self):
        html = self.client.get(reverse("content:blog")).content.decode()
        self.assertIn("Fully Funded Fellowship 2027", html)
        self.assertNotIn("Secret draft", html)
        self.assertNotIn("Scheduled post", html)

    def test_category_filter(self):
        Post.objects.create(title="Internship at a lab", slug="lab", category=PostCategory.INTERNSHIP, body="x")
        html = self.client.get(reverse("content:blog"), {"category": "internship"}).content.decode()
        self.assertIn("Internship at a lab", html)
        self.assertNotIn("Fully Funded Fellowship 2027", html)
        self.assertEqual(self.client.get(reverse("content:blog"), {"category": "nope"}).status_code, 200)

    def test_detail_renders_paragraphs_and_links(self):
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, "<p>First paragraph.</p>", html=False)
        self.assertContains(response, 'href="https://example.org/apply"')
        self.assertContains(response, "Deadline")

    def test_body_html_is_escaped(self):
        Post.objects.create(title="XSS", slug="xss", body="<script>alert(1)</script>")
        response = self.client.get(reverse("content:post", args=["xss"]))
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_drafts_hidden_from_public_but_visible_to_staff(self):
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(self.future.get_absolute_url()).status_code, 404)
        admin = get_user_model().objects.create_superuser(email="boss@example.com", password="pw-12345-xyz")
        self.client.force_login(admin)
        self.assertContains(self.client.get(self.draft.get_absolute_url()), "Draft preview")

    def test_home_shows_latest_opportunities_card(self):
        html = self.client.get("/").content.decode()
        self.assertIn("Latest Opportunities", html)
        self.assertIn(self.post.get_absolute_url(), html)
        self.assertNotIn("Secret draft", html)

    def test_home_hides_card_without_posts(self):
        Post.objects.all().delete()
        self.assertNotContains(self.client.get("/"), "Latest Opportunities")

    def test_sitemap_lists_posts(self):
        self.assertContains(self.client.get("/sitemap.xml"), "/blog/fellowship-2027/")


class ResourceTests(ContentTestCase):
    def test_grouped_and_unpublished_hidden(self):
        Resource.objects.create(title="Academic CV template", category=ResourceCategory.CV, link="https://docs.google.com/x")
        Resource.objects.create(title="SOP sample", category=ResourceCategory.SOP, link="https://docs.google.com/y")
        Resource.objects.create(title="Hidden one", category=ResourceCategory.SOP, link="https://docs.google.com/z", published=False)
        response = self.client.get(reverse("content:resources"))
        self.assertContains(response, "CV / Resume")
        self.assertContains(response, "Statement of Purpose")
        self.assertContains(response, "https://docs.google.com/x")
        self.assertNotContains(response, "Hidden one")

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse("content:resources")), "coming soon")


class NavigationTests(ContentTestCase):
    def test_menu_items(self):
        html = self.client.get("/").content.decode()
        for label in ["Blogs", "Resources", "About Us", "Join the Community"]:
            self.assertIn(label, html)

    def test_join_popup_available_on_every_page(self):
        for path in [reverse("content:blog"), reverse("content:resources"), reverse("testimonies:list"), "/privacy/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, 'id="join"')
                self.assertContains(response, 'name="full_name"')
                self.assertNotContains(response, "chat.whatsapp.com")

    def test_admin_pages(self):
        admin = get_user_model().objects.create_superuser(email="boss@example.com", password="pw-12345-xyz")
        self.client.force_login(admin)
        for name in ["admin:content_post_changelist", "admin:content_post_add", "admin:content_resource_changelist"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
