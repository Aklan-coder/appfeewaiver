from django.db import models
from django.db.models import Count, F, Q


class CurrentLevel(models.TextChoices):
    UNDERGRADUATE = "undergraduate", "Undergraduate"
    MASTERS = "masters", "Master's"
    PHD = "phd", "PhD"
    POSTDOC = "postdoctoral", "Postdoctoral"
    OTHER = "other", "Other"


class WhatsAppGroupQuerySet(models.QuerySet):
    def with_counts(self):
        return self.annotate(assigned_count=Count("registrations"))

    def available(self):
        """Active groups that still have room, least-filled first (balanced assignment)."""
        return (
            self.filter(is_active=True)
            .with_counts()
            .filter(Q(capacity__isnull=True) | Q(assigned_count__lt=F("capacity")))
            .order_by("assigned_count", "order", "pk")
        )


class WhatsAppGroup(models.Model):
    """
    A WhatsApp community group people can be sent to. Add as many as you like
    in Django Admin; new registrations are shared evenly between active groups.
    The invite link is private: it is only ever sent by email.
    """

    name = models.CharField(max_length=80, help_text="For your reference, e.g. Community Group 1.")
    invite_link = models.URLField(
        max_length=300, help_text="The WhatsApp invite link, e.g. https://chat.whatsapp.com/…"
    )
    is_active = models.BooleanField("active", default=True, help_text="Untick to stop sending new people here.")
    capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Optional. Stop assigning website registrations once this many have been sent here.",
    )
    order = models.PositiveSmallIntegerField(default=0, help_text="Tie-breaker: lower numbers are used first.")
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WhatsAppGroupQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "WhatsApp group"

    def __str__(self):
        return self.name

    @classmethod
    def pick_for_new_registration(cls):
        return cls.objects.available().first()


class CommunityRegistration(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=80, db_index=True)
    current_level = models.CharField(max_length=20, choices=CurrentLevel.choices, db_index=True)
    field_of_study = models.CharField(max_length=150, blank=True)

    whatsapp_group = models.ForeignKey(
        WhatsAppGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registrations",
        help_text="Change this to move the person to another group, then use “Resend WhatsApp email”.",
    )
    whatsapp_link_sent = models.BooleanField(default=False, db_index=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_attempts = models.PositiveSmallIntegerField(default=0)
    email_error = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_requested_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time this email address submitted the form."
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "registration"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def first_name(self):
        return (self.full_name.split() or [""])[0]
