from django.db import models


class SuccessType(models.TextChoices):
    FULLY_FUNDED = "fully_funded", "Fully Funded"
    SCHOLARSHIP = "scholarship", "Scholarship"
    ADMISSION = "admission", "Admission"
    FEE_WAIVER = "fee_waiver", "Application Fee Waiver"
    ASSISTANTSHIP = "assistantship", "Assistantship"
    FELLOWSHIP = "fellowship", "Fellowship"
    OTHER = "other", "Other"


class TestimonyQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published=True)


class Testimony(models.Model):
    external_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="ID of the Google Sheet row this came from (blank for testimonies added by hand).",
    )
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, help_text="Private. Never shown on the website.")
    program = models.CharField("degree / program", max_length=150, blank=True)
    university = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=80, blank=True)
    success_type = models.CharField(max_length=20, choices=SuccessType.choices, default=SuccessType.OTHER)
    testimony = models.TextField(max_length=2000)
    photo_url = models.URLField(max_length=500, blank=True, help_text="Optional public image link.")
    submitted_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    published = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False, help_text="Featured testimonies are shown first.")
    keep_admin_edits = models.BooleanField(
        default=False,
        help_text="Ticked automatically when you edit this in Admin, so the Google Sheet sync won't overwrite your changes.",
    )
    is_demo = models.BooleanField(default=False, help_text="Sample data for local testing only.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TestimonyQuerySet.as_manager()

    class Meta:
        ordering = ["-featured", "-submitted_at", "-created_at"]
        verbose_name_plural = "testimonies"

    def __str__(self):
        return f"{self.name} – {self.get_success_type_display()}"

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def display_date(self):
        return self.submitted_at or self.created_at


class SyncLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    trigger = models.CharField(max_length=20, default="auto")
    rows_received = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "sync log"

    def __str__(self):
        return f"{self.started_at:%Y-%m-%d %H:%M} – {self.get_status_display()}"
