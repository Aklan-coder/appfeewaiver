from django.contrib import admin

from .models import Resource, ResourceCategory


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "kind", "is_published", "is_featured", "published_at"]
    list_filter = ["is_published", "is_featured", "kind", "category", "published_at"]
    list_editable = ["is_published", "is_featured"]
    search_fields = ["title", "summary", "body"]
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ["title"]}
    list_select_related = ["category"]
    raw_id_fields = ["author"]
    actions = ["publish", "unpublish"]

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected")
    def publish(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description="Unpublish selected")
    def unpublish(self, request, queryset):
        queryset.update(is_published=False)
