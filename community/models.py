from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel
from core.utils import unique_slugify

SUCCESS_STORIES_SLUG = "success-stories"


class PostCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "post categories"

    def __str__(self):
        return self.name

    @property
    def is_success_stories(self):
        return self.slug == SUCCESS_STORIES_SLUG


class AchievementType(models.TextChoices):
    ADMISSION = "admission", "Admission received"
    SCHOLARSHIP = "scholarship", "Scholarship received"
    FULLY_FUNDED = "fully_funded", "Fully funded offer"
    ASSISTANTSHIP = "assistantship", "Assistantship received"
    FEE_WAIVED = "fee_waived", "Application fee waived"
    FELLOWSHIP = "fellowship", "Fellowship received"
    VISA = "visa", "Visa approved"
    OTHER = "other", "Other achievement"


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Post.Status.PUBLISHED)

    def with_counts(self):
        return self.annotate(
            num_comments=models.Count(
                "comments", filter=models.Q(comments__status=Comment.Status.PUBLISHED), distinct=True
            ),
            num_reactions=models.Count("reactions", distinct=True),
        )

    def for_listing(self):
        return self.published().select_related("author", "author__profile", "category").with_counts()


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        REMOVED = "removed", "Removed by moderator"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(PostCategory, on_delete=models.PROTECT, related_name="posts")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField(max_length=10000)
    external_link = models.URLField("external link (optional)", blank=True, max_length=500)
    achievement_type = models.CharField(
        max_length=20,
        choices=AchievementType.choices,
        blank=True,
        help_text="For success stories only.",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False, help_text="Pinned posts appear first in the feed.")

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "status", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("community:post_detail", args=[self.slug])

    @property
    def is_success_story(self):
        return self.category.slug == SUCCESS_STORIES_SLUG


class Comment(TimeStampedModel):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        REMOVED = "removed", "Removed by moderator"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    body = models.TextField(max_length=3000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "status", "created_at"])]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"

    def get_absolute_url(self):
        return f"{self.post.get_absolute_url()}#comment-{self.pk}"


class Reaction(models.Model):
    """A 'like' on a post. One per member per post."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_reaction_per_user_post")]


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_saved_post")]
