from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models

SITE_SETTINGS_CACHE_KEY = "core:site_settings"


class SiteSettings(models.Model):
    """
    One row of settings, edited in Django Admin → Site settings.
    Every change here shows on the website immediately: no code change,
    GitHub commit or redeploy needed.

    WhatsApp invite links are NOT stored here: they live in
    Registrations → WhatsApp groups, so you can run several groups.
    """

    site_name = models.CharField(max_length=80, default="App Fee Waiver")
    displayed_member_count = models.CharField(
        max_length=30, default="2,000+", help_text="Shown in the headline and stats, e.g. 2,000+"
    )
    contact_email = models.EmailField(
        default="appfeewaiver@gmail.com", help_text="Shown on the site for questions and registration problems."
    )
    registration_enabled = models.BooleanField(
        default=True, help_text="Untick to pause new registrations (the form is replaced by a short notice)."
    )
    homepage_announcement = models.CharField(
        max_length=200, blank=True, help_text="Optional one-line message shown at the top of the site."
    )

    # FAQ answer that depends on your policy (left blank = question hidden)
    community_free_answer = models.TextField(
        "answer to “Is the community free?”",
        blank=True,
        help_text="Write your actual policy. The question is hidden on the site while this is empty.",
    )

    # Testimonies
    testimony_form_url = models.URLField(
        "Google testimony form URL", blank=True, help_text="Opens when people click “Share Your Story” on the Funding Testimonies page."
    )
    testimony_sync_url = models.URLField(
        "Google Apps Script sync URL",
        blank=True,
        help_text="The web-app URL from docs/GOOGLE_SHEET_SETUP.md. Only approved rows are imported.",
    )
    testimony_sync_interval_minutes = models.PositiveSmallIntegerField(
        default=60, help_text="How often the site checks the Google Sheet for newly approved testimonies."
    )

    # Social links (icons only appear for links you fill in)
    x_url = models.URLField("X (Twitter) URL", blank=True)
    linkedin_url = models.URLField("LinkedIn URL", blank=True)
    youtube_url = models.URLField("YouTube URL", blank=True)
    instagram_url = models.URLField("Instagram URL", blank=True)

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

    @classmethod
    def load(cls):
        obj = cache.get(SITE_SETTINGS_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(SITE_SETTINGS_CACHE_KEY, obj, 60)
        return obj

    @property
    def social_links(self):
        links = [
            ("x", "X", self.x_url),
            ("linkedin", "LinkedIn", self.linkedin_url),
            ("youtube", "YouTube", self.youtube_url),
            ("instagram", "Instagram", self.instagram_url),
        ]
        return [(key, label, url) for key, label, url in links if url]
