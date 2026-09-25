from datetime import timedelta

from django.contrib import admin
from django.utils import timezone


class AFWAdminSite(admin.AdminSite):
    site_header = "App Fee Waiver Admin"
    site_title = "App Fee Waiver Admin"
    index_title = "Dashboard"
    index_template = "admin/afw_index.html"

    def index(self, request, extra_context=None):
        from registrations.models import CommunityRegistration, WhatsAppGroup
        from testimonies.models import SyncLog, Testimony

        week_ago = timezone.now() - timedelta(days=7)
        registrations = CommunityRegistration.objects.filter(is_demo=False)
        testimonies = Testimony.objects.filter(is_demo=False)
        stats = [
            ("Total Registrations", registrations.count(), "/admin/registrations/communityregistration/"),
            (
                "Registrations — Last 7 Days",
                registrations.filter(created_at__gte=week_ago).count(),
                "/admin/registrations/communityregistration/?created_at__gte="
                + week_ago.date().isoformat(),
            ),
            ("Published Testimonies", testimonies.filter(published=True).count(), "/admin/testimonies/testimony/?published__exact=1"),
            ("Unpublished Testimonies", testimonies.filter(published=False).count(), "/admin/testimonies/testimony/?published__exact=0"),
            (
                "Email Delivery Failures",
                registrations.filter(whatsapp_link_sent=False).count(),
                "/admin/registrations/communityregistration/?whatsapp_link_sent__exact=0",
            ),
        ]
        extra_context = {
            **(extra_context or {}),
            "dashboard_stats": stats,
            "whatsapp_groups": WhatsAppGroup.objects.with_counts().order_by("order", "pk"),
            "last_sync": SyncLog.objects.first(),
        }
        return super().index(request, extra_context)
