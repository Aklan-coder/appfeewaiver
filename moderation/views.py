from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from community.models import Comment, Post
from core.permissions import moderator_required, participation_required
from core.utils import paginate, rate_limit
from notifications.models import Notification
from notifications.services import notify
from opportunities.models import Opportunity

from .forms import ReportForm, ResolveReportForm
from .models import Report


def _create_report(request, **target):
    form = ReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a reason for your report.")
        return
    report = form.save(commit=False)
    report.reporter = request.user
    for key, value in target.items():
        setattr(report, key, value)
    try:
        with transaction.atomic():
            report.save()
    except IntegrityError:
        messages.info(request, "You have already reported this. Our moderators will review it.")
        return
    messages.success(request, "Thank you. Your report has been sent to the moderators.")


@require_POST
@participation_required
@rate_limit("report", limit=20, period=3600)
def report_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status=Post.Status.PUBLISHED)
    if post.author_id == request.user.pk:
        messages.info(request, "You can't report your own post. You can edit or delete it instead.")
    else:
        _create_report(request, post=post)
    return redirect(post)


@require_POST
@participation_required
@rate_limit("report", limit=20, period=3600)
def report_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk, status=Comment.Status.PUBLISHED)
    if comment.author_id == request.user.pk:
        messages.info(request, "You can't report your own comment.")
    else:
        _create_report(request, comment=comment)
    return redirect(comment.get_absolute_url())


@moderator_required
def queue(request):
    tab = request.GET.get("tab", "reports")
    context = {
        "tab": tab,
        "open_reports_count": Report.objects.filter(status=Report.Status.OPEN).count(),
        "pending_opportunities_count": Opportunity.objects.filter(status=Opportunity.Status.SUBMITTED).count(),
    }
    if tab == "opportunities":
        items = (
            Opportunity.objects.filter(status=Opportunity.Status.SUBMITTED)
            .select_related("opportunity_type", "posted_by")
            .order_by("created_at")
        )
    elif tab == "resolved":
        items = Report.objects.exclude(status=Report.Status.OPEN).select_related(
            "reporter", "post", "comment", "resolved_by"
        ).order_by("-resolved_at")
    else:
        tab = context["tab"] = "reports"
        items = (
            Report.objects.filter(status=Report.Status.OPEN)
            .select_related("reporter", "post", "post__author", "comment", "comment__author", "comment__post")
            .order_by("created_at")
        )
    context["page_obj"] = paginate(request, items, 20)
    context["resolve_form"] = ResolveReportForm()
    return render(request, "moderation/queue.html", context)


def _remove_target(target):
    target.status = target.Status.REMOVED
    target.save(update_fields=["status", "updated_at"])


@require_POST
@moderator_required
def resolve_report(request, pk):
    report = get_object_or_404(Report.objects.select_related("post", "comment"), pk=pk)
    form = ResolveReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose an action.")
        return redirect("moderation:queue")
    action = form.cleaned_data["action"]
    note = form.cleaned_data["note"]
    target = report.target
    author = target.author if target else None

    if action == "dismiss":
        report.status = Report.Status.DISMISSED
    else:
        report.status = Report.Status.ACTIONED
        if target:
            _remove_target(target)
            # Resolve other open reports about the same item too.
            same = Report.objects.filter(status=Report.Status.OPEN).exclude(pk=report.pk)
            same = same.filter(post=report.post) if report.post_id else same.filter(comment=report.comment)
            same.update(status=Report.Status.ACTIONED, resolved_by=request.user, resolved_at=timezone.now())
        if author and not author.is_superuser:
            if action in ("remove_warn", "remove_suspend"):
                author.warning_count += 1
                fields = ["warning_count"]
                text = "A moderator removed your content for breaking the Community Guidelines."
                if action == "remove_suspend":
                    author.suspended_until = timezone.now() + timedelta(days=7)
                    author.suspension_reason = note[:255]
                    fields += ["suspended_until", "suspension_reason"]
                    text += " Your account is suspended from posting for 7 days."
                author.save(update_fields=fields)
                if note:
                    text += f" Note: {note}"
                notify(author, Notification.Kind.MODERATION, text, "/community-guidelines/")

    report.resolved_by = request.user
    report.resolved_at = timezone.now()
    report.resolution_note = note
    report.save()
    messages.success(request, "Report resolved.")
    return redirect("moderation:queue")


@require_POST
@moderator_required
def remove_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.status == Post.Status.REMOVED:
        post.status = Post.Status.PUBLISHED
        messages.success(request, "Post restored.")
    else:
        post.status = Post.Status.REMOVED
        messages.success(request, "Post removed from the community.")
    post.save(update_fields=["status", "updated_at"])
    return redirect(post)


@require_POST
@moderator_required
def remove_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    comment.status = Comment.Status.REMOVED if comment.status == Comment.Status.PUBLISHED else Comment.Status.PUBLISHED
    comment.save(update_fields=["status", "updated_at"])
    messages.success(request, "Comment updated.")
    return redirect(comment.post)
