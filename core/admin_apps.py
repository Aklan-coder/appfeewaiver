from django.contrib.admin.apps import AdminConfig


class AFWAdminConfig(AdminConfig):
    """Use the branded admin site (with the dashboard) instead of Django's default."""

    default_site = "core.admin_site.AFWAdminSite"
