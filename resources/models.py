from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import TimeStampedModel
from core.utils import unique_slugify


class ResourceCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "resource categories"

    def __str__(self):
        return self.name


class ResourceQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Resource(TimeStampedModel):
    class Kind(models.TextChoices):
        ARTICLE = "article", "Article"
        GUIDE = "guide", "Guide"
        LINK = "link", "External link"
        TEMPLATE = "template", "Template"
        CHECKLIST = "checklist", "Checklist"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.ForeignKey(ResourceCategory, on_delete=models.PROTECT, related_name="resources")
    kind = models.CharField("resource type", max_length=12, choices=Kind.choices, default=Kind.GUIDE)
    summary = models.CharField(max_length=300)
    body = models.TextField(
        blank=True,
        help_text=(
            "Plain text. Blank lines start new paragraphs. For checklists, start each item "
            "on its own line with '- '."
        ),
    )
    external_url = models.URLField(blank=True, max_length=500)
    is_published = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, help_text="Shown in Quick Resources on the homepage.")
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    objects = ResourceQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("resources:detail", args=[self.slug])

    @property
    def checklist_items(self):
        """Lines starting with '- ' become checklist items."""
        return [line[2:].strip() for line in self.body.splitlines() if line.strip().startswith("- ")]

    @property
    def body_without_checklist(self):
        return "\n".join(line for line in self.body.splitlines() if not line.strip().startswith("- "))
