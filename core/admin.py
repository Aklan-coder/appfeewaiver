from django.contrib import admin

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Email addresses",
            {
                "description": (
                    "Every email button on the website uses these addresses. If all requests go to one inbox, "
                    "fill in only the Primary email and leave the others blank."
                ),
                "fields": (
                    "primary_email",
                    "contact_email",
                    "cv_review_email",
                    "sop_review_email",
                    "appointment_email",
                    "support_email",
                    "partnership_email",
                ),
            },
        ),
        ("Community", {"fields": ("member_count_display", "community_group_name", "community_group_url")}),
        ("Site-wide banner", {"fields": ("announcement_banner",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
