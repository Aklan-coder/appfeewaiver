from django.core.management.base import BaseCommand

from testimonies.sync import run_sync


class Command(BaseCommand):
    help = "Import newly approved testimonies from the Google Sheet (safe to run any time)."

    def handle(self, *args, **options):
        log = run_sync(trigger="command")
        style = self.style.SUCCESS if log.status == "success" else self.style.ERROR
        self.stdout.write(style(f"{log.get_status_display()}: {log.message}"))
