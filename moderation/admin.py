from django.contrib import admin, messages
from django.utils import timezone

from community.models import Comment, Post

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "reason", "target_label", "reporter", "status", "created_at", "resolved_by"]
    list_filter = ["status", "reason", "created_at"]
    search_fields = ["details", "post__title", "comment__body", "reporter__email"]
    date_hierarchy = "created_at"
    raw_id_fields = ["reporter", "post", "comment", "resolved_by"]
    list_select_related = ["reporter", "post", "comment", "resolved_by"]
    readonly_fields = ["created_at"]
    list_per_page = 50
    actions = ["dismiss_reports", "remove_reported_content"]

    @admin.action(description="Dismiss selected reports")
    def dismiss_reports(self, request, queryset):
        n = queryset.filter(status=Report.Status.OPEN).update(
            status=Report.Status.DISMISSED, resolved_by=request.user, resolved_at=timezone.now()
        )
        self.message_user(request, f"{n} report(s) dismissed.", messages.SUCCESS)

    @admin.action(description="Remove the reported content and close reports")
    def remove_reported_content(self, request, queryset):
        post_ids = [r.post_id for r in queryset if r.post_id]
        comment_ids = [r.comment_id for r in queryset if r.comment_id]
        Post.objects.filter(pk__in=post_ids).update(status=Post.Status.REMOVED)
        Comment.objects.filter(pk__in=comment_ids).update(status=Comment.Status.REMOVED)
        n = queryset.update(status=Report.Status.ACTIONED, resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f"Content removed; {n} report(s) closed.", messages.WARNING)
