from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return ["core:home", "content:blog", "content:resources", "testimonies:list", "core:privacy"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return {"core:home": 1.0, "testimonies:list": 0.8}.get(item, 0.3)


class PostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        from content.models import Post

        return Post.objects.published().filter(is_demo=False)

    def lastmod(self, post):
        return post.updated_at


sitemaps = {"static": StaticSitemap, "posts": PostSitemap}
