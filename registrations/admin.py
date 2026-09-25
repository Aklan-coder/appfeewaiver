import csv
from functools import partial

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone

from .emails import send_welcome_email
from .models import CommunityRegistration, WhatsAppGroup


@admin.register(WhatsAppGroup)
class WhatsAppGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "capacity", "assigned", "order", "masked_link", "updated_at"]
    list_editable = ["is_active", "order"]
    fields = ["name", "invite_link", "is_active", "capacity", "order", "notes"]

    def get_queryset(self, request):
        return super().get_queryset(request).with_counts()

    @admin.display(description="Website registrations assigned", ordering="assigned_count")
    def assigned(self, obj):
        return obj.assigned_count

    @admin.display(description="Invite link")
    def masked_link(self, obj):
        link = obj.invite_link
        return f"{link[:28]}…" if len(link) > 30 else link


class LinkSentFilter(admin.SimpleListFilter):
    title = "link sent"
    parameter_name = "whatsapp_link_sent__exact"

    def lookups(self, request, model_admin):
        return [("1", "Yes"), ("0", "No (email failed or not sent)")]

    def queryset(self, request, queryset):
        if self.value() in ("0", "1"):
            return queryset.filter(whatsapp_link_sent=self.value() == "1")
        return queryset


@admin.register(CommunityRegistration)
class CommunityRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "email",
        "country",
        "current_level",
        "field_of_study",
        "created_at",
        "whatsapp_group",
        "link_sent",
    ]
    list_editable = ["whatsapp_group"]
    list_filter = [LinkSentFilter, "whatsapp_group", "current_level", "country", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["full_name", "email"]
    date_hierarchy = "created_at"
    list_select_related = ["whatsapp_group"]
    list_per_page = 50
    readonly_fields = [
        "created_at",
        "last_requested_at",
        "whatsapp_link_sent",
        "email_sent_at",
        "email_attempts",
        "email_error",
        "ip_address",
    ]
    fieldsets = (
        ("Registrant", {"fields": ("full_name", "email", "country", "current_level", "field_of_study")}),
        ("WhatsApp group", {"fields": ("whatsapp_group",)}),
        (
            "Email delivery",
            {"fields": ("whatsapp_link_sent", "email_sent_at", "email_attempts", "email_error")},
        ),
        ("Record", {"fields": ("created_at", "last_requested_at", "ip_address", "is_demo")}),
    )
    actions = ["resend_whatsapp_email", "export_csv"]

    @admin.display(description="Link sent", boolean=True, ordering="whatsapp_link_sent")
    def link_sent(self, obj):
        return obj.whatsapp_link_sent

    @admin.action(description="Resend WhatsApp email")
    def resend_whatsapp_email(self, request, queryset):
        sent = failed = 0
        for registration in queryset.select_related("whatsapp_group"):
            if registration.whatsapp_group is None or not registration.whatsapp_group.is_active:
                registration.whatsapp_group = WhatsAppGroup.pick_for_new_registration() or registration.whatsapp_group
                registration.save(update_fields=["whatsapp_group"])
            if send_welcome_email(registration):
                sent += 1
            else:
                failed += 1
        if sent:
            self.message_user(request, f"Sent {sent} email(s).", messages.SUCCESS)
        if failed:
            self.message_user(
                request, f"{failed} email(s) failed. Open a registration to see the error.", messages.ERROR
            )

    @admin.action(description="Export selected to CSV (spreadsheet)")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        stamp = timezone.now().strftime("%Y%m%d-%H%M")
        response["Content-Disposition"] = f'attachment; filename="registrations-{stamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["Full name", "Email", "Country", "Current level", "Field of study", "Registered", "WhatsApp group", "Link sent"]
        )
        for r in queryset.select_related("whatsapp_group"):
            writer.writerow(
                [
                    r.full_name,
                    r.email,
                    r.country,
                    r.get_current_level_display(),
                    r.field_of_study,
                    r.created_at.strftime("%Y-%m-%d %H:%M"),
                    r.whatsapp_group.name if r.whatsapp_group else "",
                    "Yes" if r.whatsapp_link_sent else "No",
                ]
            )
        return response

    def get_actions(self, request):
        """Add one 'Move to …' action per WhatsApp group, so new groups appear automatically."""
        actions = super().get_actions(request)
        for group in WhatsAppGroup.objects.all():
            name = f"move_to_group_{group.pk}"
            actions[name] = (
                partial(self._move_to_group, group=group),
                name,
                f"Move selected to “{group.name}” and email them the new link",
            )
        return actions

    def _move_to_group(self, modeladmin, request, queryset, group):
        moved = sent = 0
        for registration in queryset:
            registration.whatsapp_group = group
            registration.save(update_fields=["whatsapp_group"])
            moved += 1
            sent += send_welcome_email(registration)
        self.message_user(request, f"Moved {moved} registration(s) to {group.name}; {sent} email(s) sent.", messages.SUCCESS)
