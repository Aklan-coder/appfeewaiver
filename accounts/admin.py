from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils import timezone

from .models import Profile, User


class EmailUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name")


class EmailUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = EmailUserCreationForm
    form = EmailUserChangeForm
    inlines = [ProfileInline]
    ordering = ["-date_joined"]
    list_display = [
        "email",
        "full_name",
        "handle",
        "email_verified",
        "is_active",
        "is_staff",
        "role",
        "warning_count",
        "suspended_until",
        "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser", "email_verified", "groups", "is_demo", "date_joined"]
    search_fields = ["email", "full_name", "handle"]
    date_hierarchy = "date_joined"
    readonly_fields = ["date_joined", "last_login"]
    list_per_page = 50
    actions = ["make_moderator", "remove_moderator", "suspend_7_days", "lift_suspension", "deactivate"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Public identity", {"fields": ("full_name", "handle", "email_verified")}),
        ("Moderation", {"fields": ("warning_count", "suspended_until", "suspension_reason")}),
        (
            "Permissions",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "description": "Moderators: add to the 'Moderator' group and tick 'Staff status' so they can use this admin.",
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined", "is_demo")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),
    )

    @admin.display(description="Role")
    def role(self, obj):
        if obj.is_superuser:
            return "Administrator"
        if obj.groups.filter(name="Moderator").exists():
            return "Moderator"
        return "Member"

    @admin.action(description="Make selected members Moderators")
    def make_moderator(self, request, queryset):
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name="Moderator")
        for user in queryset:
            user.groups.add(group)
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=["is_staff"])
        self.message_user(request, f"{queryset.count()} member(s) are now moderators.", messages.SUCCESS)

    @admin.action(description="Remove Moderator role")
    def remove_moderator(self, request, queryset):
        from django.contrib.auth.models import Group

        group = Group.objects.filter(name="Moderator").first()
        for user in queryset.filter(is_superuser=False):
            if group:
                user.groups.remove(group)
            user.is_staff = False
            user.save(update_fields=["is_staff"])
        self.message_user(request, "Moderator role removed.", messages.SUCCESS)

    @admin.action(description="Suspend from posting for 7 days")
    def suspend_7_days(self, request, queryset):
        until = timezone.now() + timedelta(days=7)
        count = queryset.filter(is_superuser=False).update(suspended_until=until)
        self.message_user(request, f"{count} member(s) suspended until {until:%Y-%m-%d}.", messages.WARNING)

    @admin.action(description="Lift suspension")
    def lift_suspension(self, request, queryset):
        count = queryset.update(suspended_until=None, suspension_reason="")
        self.message_user(request, f"Suspension lifted for {count} member(s).", messages.SUCCESS)

    @admin.action(description="Deactivate accounts (cannot log in)")
    def deactivate(self, request, queryset):
        count = queryset.filter(is_superuser=False).update(is_active=False)
        self.message_user(request, f"{count} account(s) deactivated.", messages.WARNING)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "country", "institution", "field_of_study", "degree_level", "updated_at"]
    list_filter = ["degree_level", "show_country", "show_institution"]
    search_fields = ["user__email", "user__full_name", "country", "institution", "field_of_study"]
    list_select_related = ["user"]
