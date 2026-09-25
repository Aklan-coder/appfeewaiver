from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Website", {"fields": ("site_name", "displayed_member_count", "contact_email", "homepage_announcement")}),
        (
            "Registration",
            {
                "fields": ("registration_enabled",),
                "description": "WhatsApp invite links are managed under Community registrations → WhatsApp groups.",
            },
        ),
        (
            "Funding testimonies (Google Form)",
            {"fields": ("testimony_form_url", "testimony_sync_url", "testimony_sync_interval_minutes")},
        ),
        ("FAQ", {"fields": ("community_free_answer",)}),
        (
            "Social media (optional)",
            {"fields": ("x_url", "linkedin_url", "youtube_url", "instagram_url"), "description": "Icons only appear for links you fill in."},
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Go straight to the single settings record.
        from django.shortcuts import redirect

        obj = SiteSettings.load()
        return redirect("admin:core_sitesettings_change", obj.pk)
