"""Remove everything created by `load_demo_data`."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from opportunities.models import Opportunity
from resources.models import Resource

User = get_user_model()


class Command(BaseCommand):
    help = "Delete all demo users and the content they created."

    @transaction.atomic
    def handle(self, *args, **options):
        demo_users = User.objects.filter(is_demo=True)
        opps, _ = Opportunity.objects.filter(posted_by__in=demo_users).delete()
        resources, _ = Resource.objects.filter(author__in=demo_users).delete()
        # Posts, comments, reactions, saves, reports and notifications cascade with the users.
        users, _ = demo_users.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Removed demo data (users and related rows: {users}, opportunities: {opps}, resources: {resources})."
        ))
