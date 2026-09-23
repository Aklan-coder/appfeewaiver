from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

SITE_SETTINGS_CACHE_KEY = "core:site_settings"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    """
    Single-row configuration editable from Django Admin.

    Every email button on the site (CV review, SOP review, appointments,
    contact) reads from here, so changing an address in the admin updates
    the whole site immediately. Leave a specific address blank to fall back
    to the primary email.
    """

    primary_email = models.EmailField(
        help_text="Main App Fee Waiver address. Used wherever a specific address below is left blank."
    )
    contact_email = models.EmailField(blank=True, help_text="General inquiries.")
    cv_review_email = models.EmailField(blank=True, help_text="Where members send CVs for review.")
    sop_review_email = models.EmailField(blank=True, help_text="Where members send SOPs for review.")
    appointment_email = models.EmailField(blank=True, help_text="Where appointment requests go.")
    support_email = models.EmailField(blank=True, help_text="Account / technical support.")
    partnership_email = models.EmailField(blank=True, help_text="Partnerships and collaborations.")

    member_count_display = models.CharField(
        max_length=30,
        default="2,000+",
        help_text="Community size shown on the site (the wider community, not only website accounts).",
    )
    community_group_name = models.CharField(
        max_length=80, blank=True, help_text="Optional, e.g. 'App Fee Waiver WhatsApp Group'."
    )
    community_group_url = models.URLField(
        blank=True, help_text="Optional invite link. The 'Join Our Group' card only appears when this is set."
    )
    announcement_banner = models.CharField(
        max_length=200, blank=True, help_text="Optional short message shown at the top of every page."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def clean(self):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one Site Settings record can exist. Edit the existing one.")

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce a single row
        super().save(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        cache.delete(SITE_SETTINGS_CACHE_KEY)
        return super().delete(*args, **kwargs)

    @classmethod
    def load(cls):
        obj = cache.get(SITE_SETTINGS_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1, defaults={"primary_email": "appfeewaiver@gmail.com"})
            cache.set(SITE_SETTINGS_CACHE_KEY, obj, 300)
        return obj

    # Resolved addresses (fall back to the primary email)
    def _resolve(self, value):
        return value or self.primary_email

    @property
    def contact(self):
        return self._resolve(self.contact_email)

    @property
    def cv_review(self):
        return self._resolve(self.cv_review_email)

    @property
    def sop_review(self):
        return self._resolve(self.sop_review_email)

    @property
    def appointment(self):
        return self._resolve(self.appointment_email)

    @property
    def support(self):
        return self._resolve(self.support_email)

    @property
    def partnership(self):
        return self._resolve(self.partnership_email)
