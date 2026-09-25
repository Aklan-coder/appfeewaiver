from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html

from .models import SyncLog, Testimony
from .sync import run_sync


@admin.register(Testimony)
class TestimonyAdmin(admin.ModelAdmin):
    change_list_template = "admin/testimonies/testimony/change_list.html"
    list_display = [
        "name",
        "university",
        "program",
        "country",
        "success_type",
        "display_date",
        "published",
        "featured",
        "source",
    ]
    list_editable = ["published", "featured"]
    list_filter = ["published", "featured", "success_type", "is_demo"]
    search_fields = ["name", "university", "program", "country", "testimony"]
    readonly_fields = ["external_id", "imported_at", "created_at", "updated_at", "photo_preview"]
    fieldsets = (
        ("On the website", {"fields": ("published", "featured")}),
        ("Testimony", {"fields": ("name", "success_type", "program", "university", "country", "testimony")}),
        ("Photo", {"fields": ("photo_url", "photo_preview")}),
        ("Private", {"fields": ("email",), "description": "Never shown on the website."}),
        (
            "Google Sheet sync",
            {"fields": ("external_id", "submitted_at", "imported_at", "keep_admin_edits", "is_demo", "created_at", "updated_at")},
        ),
    )
    actions = ["publish", "unpublish", "feature", "unfeature"]

    @admin.display(description="Date", ordering="submitted_at")
    def display_date(self, obj):
        return obj.display_date.strftime("%b %d, %Y")

    @admin.display(description="Source")
    def source(self, obj):
        return "Google Sheet" if obj.external_id else "Added in admin"

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="height:80px;border-radius:50%">', obj.photo_url)
        return "—"

    def save_model(self, request, obj, form, change):
        # Protect your edits from being overwritten by the next Google Sheet sync.
        if change and obj.external_id and form.changed_data and set(form.changed_data) - {"published", "featured"}:
            obj.keep_admin_edits = True
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected")
    def publish(self, request, queryset):
        self.message_user(request, f"{queryset.update(published=True)} published.", messages.SUCCESS)

    @admin.action(description="Unpublish selected (hide from website)")
    def unpublish(self, request, queryset):
        self.message_user(request, f"{queryset.update(published=False)} hidden.", messages.SUCCESS)

    @admin.action(description="Feature selected")
    def feature(self, request, queryset):
        queryset.update(featured=True)

    @admin.action(description="Unfeature selected")
    def unfeature(self, request, queryset):
        queryset.update(featured=False)

    def get_urls(self):
        return [
            path("sync-now/", self.admin_site.admin_view(self.sync_now), name="testimonies_sync_now"),
        ] + super().get_urls()

    def sync_now(self, request):
        if request.method != "POST":
            return redirect("admin:testimonies_testimony_changelist")
        log = run_sync(trigger="manual")
        level = messages.SUCCESS if log.status == SyncLog.Status.SUCCESS else messages.ERROR
        self.message_user(request, f"Google Sheet sync – {log.get_status_display()}: {log.message}", level)
        return redirect("admin:testimonies_testimony_changelist")


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ["started_at", "status", "trigger", "rows_received", "created", "updated", "skipped", "message"]
    list_filter = ["status", "trigger"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
