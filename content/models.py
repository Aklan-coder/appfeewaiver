"""
Blog posts and downloadable resources (CV/SOP formats), written by admins only.

Files are NOT uploaded to the website: Render's free plan has no permanent disk, so
uploads would disappear on every deploy. Put the file in Google Drive / Google Docs
(free), set sharing to "Anyone with the link", and paste the link here.
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator


class PostCategory(models.TextChoices):
    SCHOLARSHIP = "scholarship", "Scholarships"
    FEE_WAIVER = "fee_waiver", "Application Fee Waivers"
    FELLOWSHIP = "fellowship", "Fellowships"
    INTERNSHIP = "internship", "Internships"
    ADMISSIONS = "admissions", "Admissions"
    TIPS = "tips", "Tips & Guides"
    OTHER = "other", "Other"


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published=True, published_at__lte=timezone.now())


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, help_text="Part of the web address. Filled in automatically from the title.")
    category = models.CharField(max_length=20, choices=PostCategory.choices, default=PostCategory.SCHOLARSHIP)
    excerpt = models.CharField(
        max_length=300, blank=True, help_text="Short summary for cards. Leave empty to use the start of the post."
    )
    body = models.TextField(help_text="Plain text. Leave a blank line between paragraphs. Web links become clickable.")
    cover_image_url = models.URLField(
        "cover image link", max_length=500, blank=True, help_text="Optional. A public image link (e.g. from your website or Google Drive)."
    )
    deadline = models.DateField(null=True, blank=True, help_text="Optional application deadline, shown on the post.")
    apply_url = models.URLField("official link", max_length=500, blank=True, help_text="Optional link to the official opportunity page.")
    published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(default=timezone.now, help_text="Posts dated in the future stay hidden until then.")
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "blog post"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("content:post", args=[self.slug])

    @property
    def summary(self):
        return self.excerpt or Truncator(" ".join(self.body.split())).chars(160)


class ResourceCategory(models.TextChoices):
    CV = "cv", "CV / Resume"
    SOP = "sop", "Statement of Purpose"
    PERSONAL = "personal", "Personal Statement"
    RECOMMENDATION = "recommendation", "Recommendation Letters"
    EMAIL = "email", "Emails to Professors"
    OTHER = "other", "Other"


class Resource(models.Model):
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=ResourceCategory.choices, default=ResourceCategory.CV)
    description = models.CharField(max_length=300, blank=True)
    link = models.URLField(
        max_length=500, help_text="Google Drive / Google Docs link with sharing set to “Anyone with the link can view”."
    )
    link_label = models.CharField(max_length=40, blank=True, help_text="Button text. Default: “Open”.")
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers are shown first.")
    published = models.BooleanField(default=True, db_index=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "order", "title"]

    def __str__(self):
        return self.title
