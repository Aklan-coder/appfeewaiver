from django.contrib import admin, messages

from .models import Announcement, Notification
from .services import send_announcement


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "kind", "message", "is_read", "created_at"]
    list_filter = ["kind", "is_read", "created_at"]
    search_fields = ["message", "recipient__email", "recipient__full_name"]
    date_hierarchy = "created_at"
    raw_id_fields = ["recipient", "actor"]
    list_select_related = ["recipient"]
    list_per_page = 50


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at", "sent_at", "recipients_count"]
    readonly_fields = ["sent_at", "recipients_count"]
    actions = ["send_to_all_members"]

    @admin.action(description="Send to all members as a notification")
    def send_to_all_members(self, request, queryset):
        for announcement in queryset:
            if announcement.sent_at:
                self.message_user(request, f"“{announcement}” was already sent.", messages.WARNING)
                continue
            total = send_announcement(announcement)
            self.message_user(request, f"“{announcement}” sent to {total} member(s).", messages.SUCCESS)
