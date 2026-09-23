from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        COMMENT = "comment", "Comment on your post"
        REPLY = "reply", "Reply to your comment"
        OPPORTUNITY_VERIFIED = "opp_verified", "Opportunity verified"
        ANNOUNCEMENT = "announcement", "Announcement"
        MODERATION = "moderation", "Moderation notice"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.recipient}: {self.message}"


class Announcement(models.Model):
    """
    Created in Django Admin. Use the admin action 'Send to all members' to
    deliver it as an on-site notification.
    """

    title = models.CharField(max_length=150)
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=500, blank=True, help_text="Optional link, e.g. /resources/ or a full URL.")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
