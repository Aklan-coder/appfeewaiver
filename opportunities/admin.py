from django.contrib import admin, messages
from django.utils import timezone

from notifications.models import Notification
from notifications.services import notify

from .models import Opportunity, OpportunityType, SavedOpportunity


@admin.register(OpportunityType)
class OpportunityTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "short_label", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}


class DeadlineStateFilter(admin.SimpleListFilter):
    title = "deadline"
    parameter_name = "deadline_state"

    def lookups(self, request, model_admin):
        return [("open", "Open / upcoming"), ("expired", "Expired"), ("none", "No fixed deadline")]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "open":
            return queryset.filter(deadline__gte=today)
        if self.value() == "expired":
            return queryset.filter(deadline__lt=today)
        if self.value() == "none":
            return queryset.filter(deadline__isnull=True)
        return queryset


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "organization",
        "country",
        "opportunity_type",
        "degree_level",
        "deadline",
        "status",
        "posted_by",
        "created_at",
    ]
    list_filter = ["status", "opportunity_type", "degree_level", "funding_type", DeadlineStateFilter, "country", "created_at"]
    search_fields = ["title", "organization", "country", "field_of_study", "description"]
    date_hierarchy = "created_at"
    list_select_related = ["opportunity_type", "posted_by"]
    raw_id_fields = ["posted_by", "verified_by"]
    readonly_fields = ["created_at", "updated_at", "verified_at"]
    prepopulated_fields = {"slug": ["organization", "title"]}
    list_per_page = 50
    actions = ["verify_selected", "reject_selected", "mark_submitted"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "organization", "country", "opportunity_type")}),
        ("Details", {"fields": ("degree_level", "field_of_study", "funding_type", "deadline", "deadline_note")}),
        ("Content", {"fields": ("description", "eligibility", "additional_info")}),
        ("Links", {"fields": ("official_source_url", "application_url")}),
        ("Review", {"fields": ("status", "posted_by", "verified_by", "verified_at", "review_note", "created_at", "updated_at")}),
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("opportunities.verify_opportunity"):
            for name in ("verify_selected", "reject_selected", "mark_submitted"):
                actions.pop(name, None)
        return actions

    def save_model(self, request, obj, form, change):
        if not obj.posted_by_id and not change:
            obj.posted_by = request.user
        if obj.status == Opportunity.Status.VERIFIED and not obj.verified_at:
            obj.verified_by = request.user
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="Mark selected as Verified (official source checked)")
    def verify_selected(self, request, queryset):
        count = 0
        for opp in queryset.exclude(status=Opportunity.Status.VERIFIED).select_related("posted_by"):
            opp.mark_verified(request.user)
            if opp.posted_by:
                notify(
                    opp.posted_by,
                    Notification.Kind.OPPORTUNITY_VERIFIED,
                    f"Your submitted opportunity “{opp.title[:80]}” was verified by a moderator.",
                    opp.get_absolute_url(),
                    actor=request.user,
                )
            count += 1
        self.message_user(request, f"{count} opportunity(ies) verified.", messages.SUCCESS)

    @admin.action(description="Reject selected (hide from site)")
    def reject_selected(self, request, queryset):
        n = queryset.update(status=Opportunity.Status.REJECTED)
        self.message_user(request, f"{n} opportunity(ies) rejected.", messages.WARNING)

    @admin.action(description="Set back to Community Submitted")
    def mark_submitted(self, request, queryset):
        n = queryset.update(status=Opportunity.Status.SUBMITTED, verified_by=None, verified_at=None)
        self.message_user(request, f"{n} opportunity(ies) set to Community Submitted.", messages.INFO)


@admin.register(SavedOpportunity)
class SavedOpportunityAdmin(admin.ModelAdmin):
    list_display = ["user", "opportunity", "created_at"]
    raw_id_fields = ["user", "opportunity"]
    list_select_related = ["user", "opportunity"]
