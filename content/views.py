from django.conf import settings
from django.shortcuts import get_object_or_404, render

from core.utils import paginate

from .models import Post, PostCategory, Resource, ResourceCategory


def post_list(request):
    category = request.GET.get("category", "")
    posts = Post.objects.published()
    if category in PostCategory.values:
        posts = posts.filter(category=category)
    else:
        category = ""
    return render(
        request,
        "content/post_list.html",
        {
            "page_obj": paginate(request, posts, 12),
            "categories": PostCategory.choices,
            "active_category": category,
        },
    )


def post_detail(request, slug):
    queryset = Post.objects.all() if request.user.is_staff else Post.objects.published()
    post = get_object_or_404(queryset, slug=slug)
    related = Post.objects.published().filter(category=post.category).exclude(pk=post.pk)[:3]
    return render(request, "content/post_detail.html", {"post": post, "related": related})


def resource_list(request):
    resources = Resource.objects.filter(published=True)
    labels = dict(ResourceCategory.choices)
    groups = {}
    for resource in resources:
        groups.setdefault(resource.category, []).append(resource)
    ordered = [(labels[key], groups[key]) for key in ResourceCategory.values if key in groups]
    return render(request, "content/resource_list.html", {"groups": ordered})
