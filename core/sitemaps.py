from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from community.models import Post
from opportunities.models import Opportunity
from resources.models import Resource


class StaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return [
            "core:home",
            "core:about",
            "core:contact",
            "community:feed",
            "community:success_stories",
            "opportunities:list",
            "resources:list",
            "support:expert_support",
            "support:cv_sop_review",
            "support:appointment",
            "core:guidelines",
            "core:privacy",
            "core:terms",
            "core:disclaimer",
        ]

    def location(self, item):
        return reverse(item)


class PostSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5
    limit = 1000

    def items(self):
        return Post.objects.published().order_by("-created_at")

    def lastmod(self, obj):
        return obj.updated_at


class OpportunitySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    limit = 1000

    def items(self):
        return Opportunity.objects.public().order_by("-created_at")

    def lastmod(self, obj):
        return obj.updated_at


class ResourceSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Resource.objects.published().order_by("-published_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticSitemap,
    "posts": PostSitemap,
    "opportunities": OpportunitySitemap,
    "resources": ResourceSitemap,
}
