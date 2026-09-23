import functools

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect

from .utils import safe_back_url


def is_moderator(user):
    return bool(user.is_authenticated and user.is_moderator)


def _is_fetch(request):
    return request.headers.get("x-requested-with") == "fetch"


def participation_required(view_func):
    """
    Logged-in, active, not suspended (and email-verified when required).
    Used for every action that creates or changes community content.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            if _is_fetch(request):
                return HttpResponse("Please log in first.", status=401)
            return redirect_to_login(request.get_full_path())
        if not user.can_participate:
            if user.is_suspended:
                msg = "Your account is temporarily suspended from posting. Contact support if you think this is a mistake."
            elif settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
                msg = "Please confirm your email address before posting. Check your inbox for the link."
            else:
                msg = "Your account can't post right now."
            if _is_fetch(request):
                return HttpResponse(msg, status=403)
            messages.error(request, msg)
            return redirect(safe_back_url(request))
        return view_func(request, *args, **kwargs)

    return wrapper


def moderator_required(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_moderator(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper
