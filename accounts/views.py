from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from community.models import SUCCESS_STORIES_SLUG, Post, SavedPost
from community.views import user_post_state
from core.utils import paginate, rate_limit
from opportunities.models import Opportunity, SavedOpportunity

from .forms import (
    AccountSettingsForm,
    EmailLoginForm,
    ProfileForm,
    SignupForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from .tokens import email_verification_token, send_verification_email

User = get_user_model()


@rate_limit("signup", limit=5, period=3600)
def signup(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        send_verification_email(user)
        messages.success(
            request,
            f"Welcome to App Fee Waiver, {user.display_name}! We've sent a confirmation link to your email. "
            "You can complete your profile any time.",
        )
        return redirect("core:home")
    return render(request, "accounts/signup.html", {"form": form})


@method_decorator(rate_limit("login", limit=20, period=900), name="dispatch")
class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")

    @method_decorator(rate_limit("password_reset", limit=5, period=3600))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:settings")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)


def verify_email(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and email_verification_token.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        messages.success(request, "Thank you! Your email address is confirmed.")
    elif user and user.email_verified:
        messages.info(request, "Your email address is already confirmed.")
    else:
        messages.error(request, "That confirmation link is invalid or has expired. You can request a new one.")
    return redirect("core:home")


@login_required
@require_POST
@rate_limit("resend_verification", limit=3, period=3600)
def resend_verification(request):
    if request.user.email_verified:
        messages.info(request, "Your email address is already confirmed.")
    else:
        send_verification_email(request.user)
        messages.success(request, "We've sent a new confirmation link to your email address.")
    return redirect("accounts:settings")


def profile(request, handle):
    member = get_object_or_404(User.objects.select_related("profile"), handle=handle, is_active=True)
    posts = Post.objects.for_listing().filter(author=member).order_by("-created_at")
    stats = Post.objects.published().filter(author=member).aggregate(
        total=Count("id"),
        success=Count("id", filter=Q(category__slug=SUCCESS_STORIES_SLUG)),
    )
    shared_opportunities = Opportunity.objects.public().filter(posted_by=member).count()
    tab = request.GET.get("tab", "posts")
    if tab == "success":
        posts = posts.filter(category__slug=SUCCESS_STORIES_SLUG)
    page_obj = paginate(request, posts, 10)
    return render(
        request,
        "accounts/profile.html",
        {
            **user_post_state(request, page_obj.object_list),
            "member": member,
            "member_profile": member.profile,
            "page_obj": page_obj,
            "stats": stats,
            "shared_opportunities": shared_opportunities,
            "tab": tab,
            "is_own_profile": request.user.is_authenticated and request.user.pk == member.pk,
        },
    )


@login_required
def edit_profile(request):
    profile_obj = request.user.profile
    user_form = AccountSettingsForm(request.POST or None, instance=request.user, prefix="user")
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj, prefix="profile")
    if request.method == "POST" and form.is_valid() and user_form.is_valid():
        user_form.save()
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile", handle=request.user.handle)
    return render(request, "accounts/edit_profile.html", {"form": form, "user_form": user_form})


@login_required
def account_settings(request):
    return render(request, "accounts/settings.html")


@login_required
def my_posts(request):
    posts = (
        Post.objects.filter(author=request.user)
        .select_related("category", "author", "author__profile")
        .with_counts()
        .order_by("-created_at")
    )
    return render(request, "accounts/my_posts.html", {"page_obj": paginate(request, posts, 15)})


@login_required
def saved_items(request):
    tab = request.GET.get("tab", "opportunities")
    if tab == "posts":
        items = SavedPost.objects.filter(user=request.user, post__status=Post.Status.PUBLISHED).select_related(
            "post", "post__category", "post__author"
        )
    else:
        tab = "opportunities"
        items = SavedOpportunity.objects.filter(user=request.user).exclude(
            opportunity__status=Opportunity.Status.REJECTED
        ).select_related("opportunity", "opportunity__opportunity_type")
    return render(request, "accounts/saved.html", {"tab": tab, "page_obj": paginate(request, items, 12)})
