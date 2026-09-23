from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import DegreeLevel
from core.permissions import is_moderator, moderator_required, participation_required
from core.utils import build_search_q, paginate, querystring_without_page, rate_limit, safe_back_url, search_terms
from notifications.models import Notification
from notifications.services import notify

from .forms import OpportunitySubmitForm
from .models import FundingType, Opportunity, OpportunityType, SavedOpportunity

OPPORTUNITY_SEARCH_FIELDS = [
    "title",
    "organization",
    "country",
    "field_of_study",
    "description",
    "eligibility",
    "degree_level",
    "funding_type",
    "opportunity_type__name",
]

DEADLINE_FILTERS = [
    ("", "Any deadline"),
    ("30", "Closing within 30 days"),
    ("90", "Closing within 90 days"),
    ("none", "Rolling / no fixed date"),
    ("expired", "Expired"),
]


def opportunity_list(request, type_slug=None):
    today = timezone.localdate()
    qs = Opportunity.objects.public().select_related("opportunity_type")
    types = OpportunityType.objects.all()

    selected = {
        "type": type_slug or request.GET.get("type", ""),
        "country": request.GET.get("country", "").strip(),
        "degree": request.GET.get("degree", ""),
        "funding": request.GET.get("funding", ""),
        "field": request.GET.get("field", "").strip(),
        "deadline": request.GET.get("deadline", ""),
        "verified": request.GET.get("verified", ""),
        "q": request.GET.get("q", "").strip(),
    }

    active_type = None
    if selected["type"]:
        active_type = types.filter(slug=selected["type"]).first()
        if type_slug and not active_type:
            raise Http404
        if active_type:
            qs = qs.filter(opportunity_type=active_type)
    if selected["country"]:
        qs = qs.filter(country__iexact=selected["country"])
    if selected["degree"] in DegreeLevel.values:
        qs = qs.filter(degree_level=selected["degree"])
    if selected["funding"] in FundingType.values:
        qs = qs.filter(funding_type=selected["funding"])
    if selected["field"]:
        qs = qs.filter(field_of_study__icontains=selected["field"])
    if selected["verified"] == "1":
        qs = qs.filter(status=Opportunity.Status.VERIFIED)
    if selected["q"]:
        qs = qs.filter(build_search_q(search_terms(selected["q"]), OPPORTUNITY_SEARCH_FIELDS))

    deadline = selected["deadline"]
    if deadline == "expired":
        qs = qs.filter(deadline__lt=today).order_by("-deadline")
    else:
        # Expired opportunities are hidden unless explicitly requested.
        qs = qs.open()
        if deadline in ("30", "90"):
            qs = qs.filter(deadline__isnull=False, deadline__lte=today + timedelta(days=int(deadline)))
        elif deadline == "none":
            qs = qs.filter(deadline__isnull=True)
        sort = request.GET.get("sort", "newest")
        if sort == "deadline":
            qs = qs.order_by(F("deadline").asc(nulls_last=True), "-created_at")
        else:
            qs = qs.order_by("-created_at")

    countries = (
        Opportunity.objects.public().exclude(country="").values_list("country", flat=True).distinct().order_by("country")
    )
    page_obj = paginate(request, qs, settings.OPPORTUNITIES_PER_PAGE)
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            SavedOpportunity.objects.filter(
                user=request.user, opportunity_id__in=[o.pk for o in page_obj.object_list]
            ).values_list("opportunity_id", flat=True)
        )
    return render(
        request,
        "opportunities/list.html",
        {
            "page_obj": page_obj,
            "types": types,
            "active_type": active_type,
            "countries": countries,
            "degree_levels": DegreeLevel.choices,
            "funding_types": FundingType.choices,
            "deadline_filters": DEADLINE_FILTERS,
            "selected": selected,
            "sort": request.GET.get("sort", "newest"),
            "querystring": querystring_without_page(request),
            "saved_opportunity_ids": saved_ids,
            "has_filters": any(v for k, v in selected.items() if k != "type") or bool(type_slug),
        },
    )


def opportunity_detail(request, slug):
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("opportunity_type", "posted_by", "verified_by"), slug=slug
    )
    can_moderate = is_moderator(request.user)
    if opportunity.status == Opportunity.Status.REJECTED and not can_moderate:
        raise Http404
    is_saved = (
        request.user.is_authenticated
        and SavedOpportunity.objects.filter(user=request.user, opportunity=opportunity).exists()
    )
    related = (
        Opportunity.objects.public()
        .open()
        .filter(opportunity_type=opportunity.opportunity_type)
        .exclude(pk=opportunity.pk)
        .select_related("opportunity_type")
        .order_by("-created_at")[:4]
    )
    return render(
        request,
        "opportunities/detail.html",
        {"opportunity": opportunity, "is_saved": is_saved, "can_moderate": can_moderate, "related": related},
    )


@participation_required
@rate_limit("submit_opportunity", limit=10, period=3600)
def opportunity_submit(request):
    initial = {}
    if request.GET.get("type"):
        initial["opportunity_type"] = OpportunityType.objects.filter(slug=request.GET["type"]).first()
    form = OpportunitySubmitForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        opportunity = form.save(commit=False)
        opportunity.posted_by = request.user
        opportunity.status = Opportunity.Status.SUBMITTED
        opportunity.save()
        messages.success(
            request,
            "Thank you! Your opportunity is now listed as 'Community Submitted'. "
            "A moderator will check the official source and may mark it as Verified.",
        )
        return redirect(opportunity)
    return render(request, "opportunities/submit.html", {"form": form})


@require_POST
def toggle_save(request, slug):
    is_fetch = request.headers.get("x-requested-with") == "fetch"
    if not request.user.is_authenticated:
        if is_fetch:
            return JsonResponse({"error": "login"}, status=401)
        return redirect("accounts:login")
    opportunity = get_object_or_404(Opportunity.objects.public(), slug=slug)
    deleted, _ = SavedOpportunity.objects.filter(user=request.user, opportunity=opportunity).delete()
    saved = False
    if not deleted:
        SavedOpportunity.objects.get_or_create(user=request.user, opportunity=opportunity)
        saved = True
    if is_fetch:
        return JsonResponse({"active": saved})
    messages.success(request, "Saved to your opportunities." if saved else "Removed from your saved opportunities.")
    return redirect(safe_back_url(request, opportunity.get_absolute_url()))


@require_POST
@moderator_required
def review(request, slug):
    opportunity = get_object_or_404(Opportunity.objects.select_related("posted_by"), slug=slug)
    action = request.POST.get("action")
    if action == "verify":
        opportunity.mark_verified(request.user)
        if opportunity.posted_by:
            notify(
                opportunity.posted_by,
                Notification.Kind.OPPORTUNITY_VERIFIED,
                f"Your submitted opportunity “{opportunity.title[:80]}” was verified by a moderator.",
                opportunity.get_absolute_url(),
                actor=request.user,
            )
        messages.success(request, "Opportunity marked as Verified.")
    elif action == "reject":
        opportunity.status = Opportunity.Status.REJECTED
        opportunity.review_note = request.POST.get("note", "")[:255]
        opportunity.save(update_fields=["status", "review_note", "updated_at"])
        messages.success(request, "Opportunity rejected and hidden from the site.")
    elif action == "unverify":
        opportunity.status = Opportunity.Status.SUBMITTED
        opportunity.verified_by = None
        opportunity.verified_at = None
        opportunity.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        messages.success(request, "Verification removed.")
    return redirect(safe_back_url(request, opportunity.get_absolute_url()))
