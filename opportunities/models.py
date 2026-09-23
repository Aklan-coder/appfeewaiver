from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import DegreeLevel
from core.models import TimeStampedModel
from core.utils import unique_slugify

SCHOLARSHIP_SLUG = "scholarships"
FEE_WAIVER_SLUG = "application-fee-waivers"


class OpportunityType(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    short_label = models.CharField(max_length=30, help_text="Upper-case label for badges, e.g. SCHOLARSHIP.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class FundingType(models.TextChoices):
    FULLY_FUNDED = "fully_funded", "Fully funded"
    PARTIAL = "partially_funded", "Partially funded"
    TUITION = "tuition_waiver", "Tuition waiver"
    STIPEND = "stipend", "Stipend / salary"
    FEE_WAIVER = "fee_waiver", "Application fee waiver"
    NOT_SPECIFIED = "not_specified", "Not specified"


class OpportunityQuerySet(models.QuerySet):
    def public(self):
        return self.exclude(status=Opportunity.Status.REJECTED)

    def open(self):
        today = timezone.localdate()
        return self.filter(models.Q(deadline__isnull=True) | models.Q(deadline__gte=today))


class Opportunity(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Community Submitted"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected (hidden)"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    organization = models.CharField("university / organization", max_length=200)
    country = models.CharField(max_length=80, db_index=True)
    opportunity_type = models.ForeignKey(OpportunityType, on_delete=models.PROTECT, related_name="opportunities")
    degree_level = models.CharField(max_length=20, choices=DegreeLevel.choices, db_index=True)
    field_of_study = models.CharField(max_length=150, default="Any field")
    funding_type = models.CharField(
        max_length=20, choices=FundingType.choices, default=FundingType.NOT_SPECIFIED, db_index=True
    )
    deadline = models.DateField(null=True, blank=True, db_index=True)
    deadline_note = models.CharField(
        max_length=80, blank=True, help_text="Optional, e.g. 'Rolling' or 'Varies by program'."
    )
    description = models.TextField(max_length=5000)
    eligibility = models.TextField(max_length=3000, blank=True)
    additional_info = models.TextField(max_length=3000, blank=True)
    official_source_url = models.URLField("official source URL", max_length=500)
    application_url = models.URLField("application URL", max_length=500, blank=True)

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=255, blank=True, help_text="Internal note for moderators.")

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "opportunities"
        permissions = [("verify_opportunity", "Can verify or reject opportunities")]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["opportunity_type", "status"]),
        ]

    def __str__(self):
        return f"{self.title} – {self.organization}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, f"{self.organization} {self.title}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("opportunities:detail", args=[self.slug])

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED

    @property
    def is_expired(self):
        return bool(self.deadline and self.deadline < timezone.localdate())

    @property
    def days_left(self):
        if not self.deadline:
            return None
        return (self.deadline - timezone.localdate()).days

    @property
    def type_label(self):
        return self.opportunity_type.short_label

    def mark_verified(self, moderator):
        self.status = self.Status.VERIFIED
        self.verified_by = moderator
        self.verified_at = timezone.now()
        self.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])


class SavedOpportunity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_opportunities")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "saved opportunities"
        constraints = [models.UniqueConstraint(fields=["user", "opportunity"], name="unique_saved_opportunity")]
