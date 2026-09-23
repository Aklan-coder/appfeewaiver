import functools
import re

from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.text import slugify


RESERVED_SLUGS = {"new", "submit", "success-stories", "comments", "saved", "search", "admin", "edit"}


def unique_slugify(instance, value, slug_field="slug", max_length=200):
    """Create a readable, unique slug for `instance` from `value`."""
    base = slugify(value)[: max_length - 8].strip("-") or "item"
    if base in RESERVED_SLUGS:
        base = f"{base}-post"
    model = instance.__class__
    slug = base
    n = 2
    qs = model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def safe_back_url(request, fallback="/"):
    """The page the user came from, if it is on this site; otherwise `fallback`."""
    from django.utils.http import url_has_allowed_host_and_scheme

    for candidate in (request.POST.get("next"), request.GET.get("next"), request.META.get("HTTP_REFERER")):
        if candidate and url_has_allowed_host_and_scheme(
            candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return candidate
    return fallback


def paginate(request, queryset, per_page):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))


def querystring_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(key, limit, period):
    """Return True if `key` has been used more than `limit` times in `period` seconds."""
    cache_key = f"rl:{key}"
    added = cache.add(cache_key, 1, period)
    if added:
        return False
    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, period)
        return False
    return count > limit


def rate_limit(action, limit, period, methods=("POST",)):
    """
    Simple cache-based rate limit decorator (no external service).
    Keys by user id when logged in, otherwise by IP address.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                who = f"u{request.user.pk}" if request.user.is_authenticated else f"ip{client_ip(request)}"
                if is_rate_limited(f"{action}:{who}", limit, period):
                    msg = "You're doing that too often. Please wait a few minutes and try again."
                    if request.headers.get("x-requested-with") == "fetch":
                        return HttpResponse(msg, status=429)
                    messages.error(request, msg)
                    return redirect(safe_back_url(request))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


STOPWORDS = {"a", "an", "the", "for", "in", "of", "and", "to", "on", "at", "with", "is", "my", "me", "i"}


def search_terms(query):
    """Split a search query into normalised terms ("Master's" -> "master")."""
    terms = []
    for raw in re.split(r"\s+", (query or "").strip()):
        term = raw.strip("\"'.,;:!?()").lower()
        term = re.sub(r"'s$|’s$", "", term)
        if len(term) > 1 and term not in STOPWORDS:
            terms.append(term)
    return terms[:8]


TERM_ALIASES = {
    "us": ["united states", "usa"],
    "usa": ["united states"],
    "america": ["united states"],
    "uk": ["united kingdom"],
    "phd": ["doctoral", "doctorate"],
    "masters": ["master"],
    "msc": ["master"],
    "undergrad": ["undergraduate", "bachelor"],
    "bachelors": ["bachelor", "undergraduate"],
    "cs": ["computer science"],
}


def build_search_q(terms, fields):
    """Every term (or one of its aliases) must match at least one of the fields."""
    from django.db.models import Q

    query = Q()
    for term in terms:
        term_q = Q()
        for variant in [term, *TERM_ALIASES.get(term, [])]:
            for field in fields:
                term_q |= Q(**{f"{field}__icontains": variant})
        query &= term_q
    return query
