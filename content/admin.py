from django.contrib import admin

from .models import Post, Resource


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "published", "published_at", "deadline"]
    list_editable = ["published"]
    list_filter = ["published", "category", "published_at"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "excerpt", "body")}),
        ("Opportunity details (optional)", {"fields": ("deadline", "apply_url", "cover_image_url")}),
        ("Publishing", {"fields": ("published", "published_at", "is_demo")}),
    )


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "order", "published", "link"]
    list_editable = ["order", "published"]
    list_filter = ["category", "published"]
    search_fields = ["title", "description"]
    fields = ["title", "category", "description", "link", "link_label", "order", "published", "is_demo"]
