"""Give an existing member the Moderator role:  python manage.py create_moderator someone@example.com"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Add a member to the Moderator group (and allow them into Django Admin)."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=options["email"])
        except User.DoesNotExist:
            raise CommandError("No member with that email address.")
        group, _ = Group.objects.get_or_create(name="Moderator")
        user.groups.add(group)
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        self.stdout.write(self.style.SUCCESS(f"{user.display_name} is now a moderator."))
