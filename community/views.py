from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import is_moderator, participation_required
from core.utils import build_search_q, paginate, querystring_without_page, rate_limit, search_terms
from moderation.forms import ReportForm
from notifications.models import Notification
from notifications.services import notify

from .forms import CommentEditForm, CommentForm, PostForm
from .models import SUCCESS_STORIES_SLUG, AchievementType, Comment, Post, PostCategory, Reaction, SavedPost

SORT_OPTIONS = {
    "latest": "Latest",
    "popular": "Popular",
    "discussed": "Most Discussed",
    "unanswered": "Unanswered",
}
POST_SEARCH_FIELDS = ["title", "body", "category__name"]


def _is_fetch(request):
    return request.headers.get("x-requested-with") == "fetch"


def apply_sort(queryset, sort):
    if sort == "popular":
        return queryset.order_by("-num_reactions", "-num_comments", "-created_at")
    if sort == "discussed":
        return queryset.order_by("-num_comments", "-created_at")
    if sort == "unanswered":
        return queryset.filter(num_comments=0).order_by("-created_at")
    return queryset.order_by("-is_pinned", "-created_at")


def feed(request):
    posts = Post.objects.for_listing()
    categories = PostCategory.objects.filter(is_active=True)

    category_slug = request.GET.get("category", "")
    active_category = None
    if category_slug:
        active_category = categories.filter(slug=category_slug).first()
        if active_category:
            posts = posts.filter(category=active_category)

    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(build_search_q(search_terms(query), POST_SEARCH_FIELDS))

    sort = request.GET.get("sort", "latest")
    if sort not in SORT_OPTIONS:
        sort = "latest"
    posts = apply_sort(posts, sort)

    page_obj = paginate(request, posts, settings.POSTS_PER_PAGE)
    return render(
        request,
        "community/feed.html",
        {
            "page_obj": page_obj,
            "categories": categories,
            "active_category": active_category,
            "sort": sort,
            "sort_options": SORT_OPTIONS,
            "query": query,
            "querystring": querystring_without_page(request),
            **user_post_state(request, page_obj.object_list),
        },
    )


def success_stories(request):
    stories = Post.objects.for_listing().filter(category__slug=SUCCESS_STORIES_SLUG)
    achievement = request.GET.get("achievement", "")
    if achievement in AchievementType.values:
        stories = stories.filter(achievement_type=achievement)
    page_obj = paginate(request, stories.order_by("-created_at"), 12)
    return render(
        request,
        "community/success_stories.html",
        {
            "page_obj": page_obj,
            "achievement_types": AchievementType.choices,
            "achievement": achievement,
            "querystring": querystring_without_page(request),
            **user_post_state(request, page_obj.object_list),
        },
    )


def user_post_state(request, posts):
    """Which of these posts has the current member liked / saved (one query each)."""
    if not request.user.is_authenticated:
        return {"liked_ids": set(), "saved_ids": set()}
    ids = [p.pk for p in posts]
    return {
        "liked_ids": set(Reaction.objects.filter(user=request.user, post_id__in=ids).values_list("post_id", flat=True)),
        "saved_ids": set(SavedPost.objects.filter(user=request.user, post_id__in=ids).values_list("post_id", flat=True)),
    }


def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile", "category").with_counts(), slug=slug
    )
    can_moderate = is_moderator(request.user)
    is_author = request.user.is_authenticated and post.author_id == request.user.pk
    if post.status == Post.Status.REMOVED and not (can_moderate or is_author):
        raise Http404

    replies_qs = Comment.objects.select_related("author", "author__profile").order_by("created_at")
    comments = (
        post.comments.filter(parent__isnull=True)
        .select_related("author", "author__profile")
        .prefetch_related(Prefetch("replies", queryset=replies_qs))
        .order_by("created_at")
    )
    related = (
        Post.objects.for_listing()
        .filter(category=post.category)
        .exclude(pk=post.pk)
        .order_by("-created_at")[:4]
    )
    state = user_post_state(request, [post])
    return render(
        request,
        "community/post_detail.html",
        {
            "post": post,
            "comments": comments,
            "comment_form": CommentForm(),
            "report_form": ReportForm(),
            "related_posts": related,
            "can_moderate": can_moderate,
            "is_author": is_author,
            "has_liked": post.pk in state["liked_ids"],
            "has_saved": post.pk in state["saved_ids"],
        },
    )


def _success_category_id():
    pk = PostCategory.objects.filter(slug=SUCCESS_STORIES_SLUG).values_list("pk", flat=True).first()
    return str(pk or "")


@participation_required
@rate_limit("create_post", limit=10, period=3600)
def post_create(request):
    initial = {}
    category_slug = request.GET.get("category")
    if category_slug:
        category = PostCategory.objects.filter(slug=category_slug, is_active=True).first()
        if category:
            initial["category"] = category
    form = PostForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Your post is live. Thank you for contributing!")
        return redirect(post)
    return render(
        request,
        "community/post_form.html",
        {"form": form, "is_edit": False, "success_category_id": _success_category_id()},
    )


@participation_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user, status=Post.Status.PUBLISHED)
    form = PostForm(request.POST or None, instance=post)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.edited_at = timezone.now()
        post.save()
        messages.success(request, "Your post has been updated.")
        return redirect(post)
    return render(
        request,
        "community/post_form.html",
        {"form": form, "is_edit": True, "post": post, "success_category_id": _success_category_id()},
    )


def post_delete(request, slug):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Your post has been deleted.")
        return redirect("accounts:my_posts")
    return render(request, "community/confirm_delete.html", {"object": post, "kind": "post", "cancel_url": post.get_absolute_url()})


@require_POST
@participation_required
@rate_limit("comment", limit=30, period=3600)
def comment_create(request, slug):
    post = get_object_or_404(Post.objects.select_related("author"), slug=slug, status=Post.Status.PUBLISHED)
    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Your comment could not be posted: " + " ".join(
            e for errors in form.errors.values() for e in errors
        ))
        return redirect(post)

    parent = None
    parent_id = form.cleaned_data.get("parent_id")
    if parent_id:
        parent = get_object_or_404(Comment.objects.select_related("author"), pk=parent_id, post=post)
    replied_to = parent
    if parent and parent.parent_id:  # keep threads one level deep
        parent = parent.parent

    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.parent = parent
    comment.save()

    actor = request.user
    title = post.title if len(post.title) <= 60 else post.title[:57] + "…"
    if replied_to:
        notify(
            replied_to.author,
            Notification.Kind.REPLY,
            f"{actor.display_name} replied to your comment on “{title}”",
            comment.get_absolute_url(),
            actor=actor,
        )
        if post.author_id != replied_to.author_id:
            notify(
                post.author,
                Notification.Kind.COMMENT,
                f"{actor.display_name} replied on your post “{title}”",
                comment.get_absolute_url(),
                actor=actor,
            )
    else:
        notify(
            post.author,
            Notification.Kind.COMMENT,
            f"{actor.display_name} commented on your post “{title}”",
            comment.get_absolute_url(),
            actor=actor,
        )
    messages.success(request, "Comment posted.")
    return redirect(comment.get_absolute_url())


@participation_required
def comment_edit(request, pk):
    comment = get_object_or_404(
        Comment.objects.select_related("post"), pk=pk, author=request.user, status=Comment.Status.PUBLISHED
    )
    form = CommentEditForm(request.POST or None, instance=comment)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.edited_at = timezone.now()
        comment.save()
        messages.success(request, "Comment updated.")
        return redirect(comment.get_absolute_url())
    return render(request, "community/comment_form.html", {"form": form, "comment": comment})


def comment_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk, author=request.user)
    post = comment.post
    if request.method == "POST":
        if comment.replies.exists():
            # Keep the thread readable for people who replied.
            comment.status = Comment.Status.REMOVED
            comment.body = "[deleted by author]"
            comment.save(update_fields=["status", "body", "updated_at"])
        else:
            comment.delete()
        messages.success(request, "Comment deleted.")
        return redirect(post)
    return render(
        request,
        "community/confirm_delete.html",
        {"object": comment, "kind": "comment", "cancel_url": comment.get_absolute_url()},
    )


@require_POST
@participation_required
@rate_limit("react", limit=120, period=3600)
def toggle_reaction(request, slug):
    post = get_object_or_404(Post, slug=slug, status=Post.Status.PUBLISHED)
    deleted, _ = Reaction.objects.filter(user=request.user, post=post).delete()
    liked = False
    if not deleted:
        try:
            with transaction.atomic():
                Reaction.objects.create(user=request.user, post=post)
        except IntegrityError:
            pass  # a double-click created it already
        liked = True
    count = post.reactions.count()
    if _is_fetch(request):
        return JsonResponse({"active": liked, "count": count})
    return redirect(post)


@require_POST
def toggle_save_post(request, slug):
    if not request.user.is_authenticated:
        if _is_fetch(request):
            return JsonResponse({"error": "login"}, status=401)
        return redirect("accounts:login")
    post = get_object_or_404(Post, slug=slug, status=Post.Status.PUBLISHED)
    deleted, _ = SavedPost.objects.filter(user=request.user, post=post).delete()
    saved = False
    if not deleted:
        SavedPost.objects.get_or_create(user=request.user, post=post)
        saved = True
    if _is_fetch(request):
        return JsonResponse({"active": saved})
    messages.success(request, "Post saved." if saved else "Post removed from your saved items.")
    return redirect(post)
