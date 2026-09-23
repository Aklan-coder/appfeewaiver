from django.conf import settings
from django.shortcuts import get_object_or_404, render

from core.utils import build_search_q, paginate, querystring_without_page, search_terms

from .models import Resource, ResourceCategory

RESOURCE_SEARCH_FIELDS = ["title", "summary", "body", "category__name"]


def resource_list(request):
    resources = Resource.objects.published().select_related("category")
    categories = ResourceCategory.objects.all()
    category_slug = request.GET.get("category", "")
    active_category = categories.filter(slug=category_slug).first() if category_slug else None
    if active_category:
        resources = resources.filter(category=active_category)
    kind = request.GET.get("kind", "")
    if kind in Resource.Kind.values:
        resources = resources.filter(kind=kind)
    query = request.GET.get("q", "").strip()
    if query:
        resources = resources.filter(build_search_q(search_terms(query), RESOURCE_SEARCH_FIELDS))
    return render(
        request,
        "resources/list.html",
        {
            "page_obj": paginate(request, resources, settings.RESOURCES_PER_PAGE),
            "categories": categories,
            "active_category": active_category,
            "kinds": Resource.Kind.choices,
            "kind": kind,
            "query": query,
            "querystring": querystring_without_page(request),
        },
    )


def resource_detail(request, slug):
    resource = get_object_or_404(Resource.objects.published().select_related("category"), slug=slug)
    related = (
        Resource.objects.published().filter(category=resource.category).exclude(pk=resource.pk).order_by("-published_at")[:4]
    )
    return render(request, "resources/detail.html", {"resource": resource, "related": related})
