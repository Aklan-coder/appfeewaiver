import functools

from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect


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
