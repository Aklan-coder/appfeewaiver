from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from community.models import SUCCESS_STORIES_SLUG, Post, PostCategory
from community.views import POST_SEARCH_FIELDS, user_post_state
from moderation.models import Report
from opportunities.models import FEE_WAIVER_SLUG, SCHOLARSHIP_SLUG, Opportunity, SavedOpportunity
from opportunities.views import OPPORTUNITY_SEARCH_FIELDS
from resources.models import Resource
from resources.views import RESOURCE_SEARCH_FIELDS

from .permissions import moderator_required
from .utils import build_search_q, querystring_without_page, search_terms

User = get_user_model()

CHECKLIST = [
    ("explore", "Explore opportunities", "opportunities:list"),
    ("cv", "Prepare your CV", "support:cv_sop_review"),
    ("sop", "Prepare your SOP", "support:cv_sop_review"),
    ("letters", "Request recommendation letters", "resources:list"),
    ("deadlines", "Check application deadlines", "opportunities:list"),
    ("scholarships", "Apply for scholarships", "opportunities:list"),
    ("waivers", "Request fee waivers", "opportunities:list"),
]

HOME_POST_TABS = [
    ("", "All Posts"),
    ("scholarships", "Scholarships"),
    ("application-fee-waivers", "Fee Waivers"),
    ("cv-sop-advice", "CV/SOP"),
    ("graduate-admissions", "Admissions"),
    ("visa-travel", "Visa & Travel"),
    (SUCCESS_STORIES_SLUG, "Success Stories"),
]

ASSISTANTSHIP_SLUGS = ["graduate-assistantships", "research-assistantships", "teaching-assistantships"]


def community_stats():
    """Only numbers that can be calculated from the database."""
    public = Opportunity.objects.public()
    return {
        "posts": Post.objects.published().count(),
        "scholarships": public.filter(opportunity_type__slug=SCHOLARSHIP_SLUG).count(),
        "fee_waivers": public.filter(opportunity_type__slug=FEE_WAIVER_SLUG).count(),
        "opportunities": public.count(),
        "countries": User.objects.filter(is_active=True)
        .exclude(profile__country="")
        .values("profile__country")
        .distinct()
        .count(),
    }


def home(request):
    today = timezone.localdate()
    open_opps = Opportunity.objects.public().open().select_related("opportunity_type")

    def latest_of(slugs):
        return list(open_opps.filter(opportunity_type__slug__in=slugs).order_by("-created_at")[:3])

    opportunity_groups = [
        ("all", "All", list(open_opps.order_by("-created_at")[:6])),
        ("scholarships", "Scholarships", latest_of([SCHOLARSHIP_SLUG])),
        ("waivers", "Fee Waivers", latest_of([FEE_WAIVER_SLUG])),
        ("assistantships", "Assistantships", latest_of(ASSISTANTSHIP_SLUGS)),
        ("fellowships", "Fellowships", latest_of(["fellowships"])),
    ]

    top_contributors = (
        User.objects.filter(is_active=True)
        .annotate(post_total=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)))
        .filter(post_total__gt=0)
        .select_related("profile")
        .order_by("-post_total")[:5]
    )

    latest_posts = list(Post.objects.for_listing().order_by("-is_pinned", "-created_at")[:6])
    saved_opportunity_ids = set()
    if request.user.is_authenticated:
        saved_opportunity_ids = set(
            SavedOpportunity.objects.filter(user=request.user).values_list("opportunity_id", flat=True)
        )
    context = {
        **user_post_state(request, latest_posts),
        "saved_opportunity_ids": saved_opportunity_ids,
        "stats": community_stats(),
        "latest_posts": latest_posts,
        "post_tabs": HOME_POST_TABS,
        "upcoming_deadlines": open_opps.filter(deadline__isnull=False, deadline__gte=today).order_by("deadline")[:5],
        "opportunity_groups": opportunity_groups,
        "success_stories": Post.objects.for_listing().filter(category__slug=SUCCESS_STORIES_SLUG).order_by("-created_at")[:3],
        "featured_resources": Resource.objects.published().filter(is_featured=True).select_related("category")[:5],
        "latest_resources": Resource.objects.published().select_related("category").order_by("-published_at")[:6],
        "top_contributors": top_contributors,
        "checklist": CHECKLIST,
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")


def contact(request):
    return render(request, "core/contact.html")


def privacy(request):
    return render(request, "core/legal/privacy.html")


def terms(request):
    return render(request, "core/legal/terms.html")


def guidelines(request):
    return render(request, "core/legal/guidelines.html")


def disclaimer(request):
    return render(request, "core/legal/disclaimer.html")


SEARCH_SCOPES = [
    ("all", "Everything"),
    ("opportunities", "Opportunities"),
    ("posts", "Community posts"),
    ("resources", "Resources"),
]
SEARCH_LIMIT_PER_TYPE = 100


def search(request):
    query = request.GET.get("q", "").strip()
    scope = request.GET.get("scope", "all")
    if scope not in dict(SEARCH_SCOPES):
        scope = "all"
    terms = search_terms(query)
    results, counts = [], {}

    if terms:
        if scope in ("all", "opportunities"):
            opps = (
                Opportunity.objects.public()
                .filter(build_search_q(terms, OPPORTUNITY_SEARCH_FIELDS))
                .select_related("opportunity_type")
                .order_by("-created_at")[:SEARCH_LIMIT_PER_TYPE]
            )
            for o in opps:
                results.append(
                    {
                        "kind": "opportunity",
                        "label": o.opportunity_type.short_label,
                        "title": o.title,
                        "subtitle": f"{o.organization} · {o.country}",
                        "snippet": o.description,
                        "url": o.get_absolute_url(),
                        "date": o.created_at,
                        "verified": o.is_verified,
                        "expired": o.is_expired,
                    }
                )
            counts["opportunities"] = len(opps)
        if scope in ("all", "posts"):
            posts = (
                Post.objects.published()
                .filter(build_search_q(terms, POST_SEARCH_FIELDS))
                .select_related("category", "author")
                .order_by("-created_at")[:SEARCH_LIMIT_PER_TYPE]
            )
            for p in posts:
                results.append(
                    {
                        "kind": "post",
                        "label": "SUCCESS STORY" if p.category.slug == SUCCESS_STORIES_SLUG else "COMMUNITY POST",
                        "title": p.title,
                        "subtitle": f"{p.category.name} · by {p.author.display_name}",
                        "snippet": p.body,
                        "url": p.get_absolute_url(),
                        "date": p.created_at,
                    }
                )
            counts["posts"] = len(posts)
        if scope in ("all", "resources"):
            resources = (
                Resource.objects.published()
                .filter(build_search_q(terms, RESOURCE_SEARCH_FIELDS))
                .select_related("category")
                .order_by("-published_at")[:SEARCH_LIMIT_PER_TYPE]
            )
            for r in resources:
                results.append(
                    {
                        "kind": "resource",
                        "label": "RESOURCE",
                        "title": r.title,
                        "subtitle": f"{r.category.name} · {r.get_kind_display()}",
                        "snippet": r.summary,
                        "url": r.get_absolute_url(),
                        "date": r.published_at,
                    }
                )
            counts["resources"] = len(resources)
        results.sort(key=lambda item: item["date"], reverse=True)

    page_obj = Paginator(results, settings.SEARCH_RESULTS_PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "core/search.html",
        {
            "query": query,
            "scope": scope,
            "scopes": SEARCH_SCOPES,
            "page_obj": page_obj,
            "counts": counts,
            "total": len(results),
            "querystring": querystring_without_page(request),
        },
    )


@moderator_required
def dashboard(request):
    now = timezone.now()
    public = Opportunity.objects.public()
    stats = [
        ("Total Members", User.objects.filter(is_active=True).count(), "users", "/admin/accounts/user/"),
        (
            "New Members (30 days)",
            User.objects.filter(date_joined__gte=now - timedelta(days=30)).count(),
            "user-plus",
            "/admin/accounts/user/",
        ),
        ("Community Posts", Post.objects.published().count(), "chat", "/admin/community/post/"),
        (
            "Scholarships",
            public.filter(opportunity_type__slug=SCHOLARSHIP_SLUG).count(),
            "award",
            f"/admin/opportunities/opportunity/?opportunity_type__slug__exact={SCHOLARSHIP_SLUG}",
        ),
        (
            "Application Fee Waivers",
            public.filter(opportunity_type__slug=FEE_WAIVER_SLUG).count(),
            "ticket",
            f"/admin/opportunities/opportunity/?opportunity_type__slug__exact={FEE_WAIVER_SLUG}",
        ),
        (
            "Pending Opportunity Reviews",
            Opportunity.objects.filter(status=Opportunity.Status.SUBMITTED).count(),
            "clock",
            "/moderation/?tab=opportunities",
        ),
        (
            "Reported Posts",
            Report.objects.filter(status=Report.Status.OPEN, post__isnull=False).count(),
            "flag",
            "/moderation/",
        ),
        ("Resources", Resource.objects.filter(is_published=True).count(), "book", "/admin/resources/resource/"),
    ]
    context = {
        "stats": stats,
        "open_comment_reports": Report.objects.filter(status=Report.Status.OPEN, comment__isnull=False).count(),
        "recent_members": User.objects.select_related("profile").order_by("-date_joined")[:8],
        "recent_posts": Post.objects.select_related("author", "category").order_by("-created_at")[:8],
        "posts_by_category": PostCategory.objects.annotate(
            total=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).order_by("-total")[:8],
    }
    return render(request, "core/dashboard.html", context)


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /moderation/",
        "Disallow: /notifications/",
        "Disallow: /dashboard/",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)
