"""
The earlier version of the site had a forum, opportunities, resources, notifications
and moderation. Their code is gone, but their database tables were deliberately LEFT
in place so nothing was deleted without your say-so.

    python manage.py drop_legacy_tables            # lists what would be removed (safe)
    python manage.py drop_legacy_tables --confirm  # actually drops those tables
"""
from django.core.management.base import BaseCommand
from django.db import connection

LEGACY_PREFIXES = ("community_", "opportunities_", "resources_", "notifications_", "moderation_")
LEGACY_EXACT = ("accounts_profile",)


class Command(BaseCommand):
    help = "List (or with --confirm, drop) database tables left over from the old forum version."

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Really drop the tables.")

    def handle(self, *args, **options):
        tables = [
            t
            for t in connection.introspection.table_names()
            if t.startswith(LEGACY_PREFIXES) or t in LEGACY_EXACT
        ]
        if not tables:
            self.stdout.write(self.style.SUCCESS("No legacy tables found."))
            return
        self.stdout.write("Legacy tables:\n  " + "\n  ".join(tables))
        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Nothing dropped. Re-run with --confirm to remove them."))
            return
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE' if connection.vendor == "postgresql" else f'DROP TABLE IF EXISTS "{table}"')
        self.stdout.write(self.style.SUCCESS(f"Dropped {len(tables)} table(s)."))
