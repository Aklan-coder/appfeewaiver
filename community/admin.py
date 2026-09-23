from django.contrib import admin, messages

from .models import Comment, Post, PostCategory, Reaction, SavedPost


@admin.register(PostCategory)
class PostCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "order", "is_active", "post_count"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]

    @admin.display(description="Posts")
    def post_count(self, obj):
        return obj.posts.count()


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ["author", "body", "status", "created_at"]
    readonly_fields = ["author", "created_at"]
    show_change_link = True


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "status", "is_pinned", "created_at"]
    list_filter = ["status", "category", "is_pinned", "achievement_type", "created_at"]
    search_fields = ["title", "body", "author__email", "author__full_name"]
    date_hierarchy = "created_at"
    list_select_related = ["author", "category"]
    raw_id_fields = ["author"]
    readonly_fields = ["created_at", "updated_at", "edited_at"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [CommentInline]
    list_per_page = 50
    actions = ["remove_posts", "restore_posts", "pin_posts", "unpin_posts"]

    @admin.action(description="Remove selected posts (hide from community)")
    def remove_posts(self, request, queryset):
        n = queryset.update(status=Post.Status.REMOVED)
        self.message_user(request, f"{n} post(s) removed.", messages.WARNING)

    @admin.action(description="Restore selected posts")
    def restore_posts(self, request, queryset):
        n = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f"{n} post(s) restored.", messages.SUCCESS)

    @admin.action(description="Pin to top of feed")
    def pin_posts(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description="Unpin")
    def unpin_posts(self, request, queryset):
        queryset.update(is_pinned=False)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["short_body", "author", "post", "parent", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["body", "author__email", "author__full_name", "post__title"]
    date_hierarchy = "created_at"
    raw_id_fields = ["author", "post", "parent"]
    list_select_related = ["author", "post"]
    list_per_page = 50
    actions = ["remove_comments", "restore_comments"]

    @admin.display(description="Comment")
    def short_body(self, obj):
        return obj.body[:80]

    @admin.action(description="Remove selected comments")
    def remove_comments(self, request, queryset):
        n = queryset.update(status=Comment.Status.REMOVED)
        self.message_user(request, f"{n} comment(s) removed.", messages.WARNING)

    @admin.action(description="Restore selected comments")
    def restore_comments(self, request, queryset):
        n = queryset.update(status=Comment.Status.PUBLISHED)
        self.message_user(request, f"{n} comment(s) restored.", messages.SUCCESS)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "created_at"]
    raw_id_fields = ["user", "post"]
    list_select_related = ["user", "post"]


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "created_at"]
    raw_id_fields = ["user", "post"]
    list_select_related = ["user", "post"]
