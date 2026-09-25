from django.core.management.base import BaseCommand

from content.models import Post, Resource
from registrations.models import CommunityRegistration, WhatsAppGroup
from testimonies.models import Testimony

from .load_demo_data import DEMO_LINK_PREFIX


class Command(BaseCommand):
    help = "Delete everything created by load_demo_data."

    def handle(self, *args, **options):
        t, _ = Testimony.objects.filter(is_demo=True).delete()
        r, _ = CommunityRegistration.objects.filter(is_demo=True).delete()
        g, _ = WhatsAppGroup.objects.filter(invite_link__startswith=DEMO_LINK_PREFIX).delete()
        p, _ = Post.objects.filter(is_demo=True).delete()
        res, _ = Resource.objects.filter(is_demo=True).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Removed {t} demo testimonies, {r} demo registrations, {g} demo groups, {p} demo posts, {res} demo resources."
        ))
