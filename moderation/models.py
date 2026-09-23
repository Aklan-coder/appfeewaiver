from django.conf import settings
from django.db import models


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        SCAM = "scam", "Scam"
        INCORRECT = "incorrect", "Incorrect information"
        HARASSMENT = "harassment", "Harassment"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        DUPLICATE = "duplicate", "Duplicate post"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Action taken"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    post = models.ForeignKey(
        "community.Post", null=True, blank=True, on_delete=models.CASCADE, related_name="reports"
    )
    comment = models.ForeignKey(
        "community.Comment", null=True, blank=True, on_delete=models.CASCADE, related_name="reports"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("review_report", "Can review reports and moderate content")]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(post__isnull=False, comment__isnull=True)
                    | models.Q(post__isnull=True, comment__isnull=False)
                ),
                name="report_targets_exactly_one_item",
            ),
            models.UniqueConstraint(
                fields=["reporter", "post"],
                condition=models.Q(status="open", post__isnull=False),
                name="one_open_report_per_post_per_user",
            ),
            models.UniqueConstraint(
                fields=["reporter", "comment"],
                condition=models.Q(status="open", comment__isnull=False),
                name="one_open_report_per_comment_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.get_reason_display()} report on {self.target_label}"

    @property
    def target(self):
        return self.post or self.comment

    @property
    def target_label(self):
        return f"post “{self.post}”" if self.post_id else f"comment #{self.comment_id}"

    @property
    def target_author(self):
        return self.target.author if self.target else None
