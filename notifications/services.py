"""Small helpers so other apps never build Notification rows by hand."""
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Notification


def notify(recipient, kind, message, url="", actor=None):
    if recipient is None or (actor is not None and recipient.pk == actor.pk):
        return None  # never notify people about their own actions
    return Notification.objects.create(recipient=recipient, actor=actor, kind=kind, message=message[:255], url=url)


def send_announcement(announcement):
    User = get_user_model()
    recipients = User.objects.filter(is_active=True).only("pk").iterator(chunk_size=500)
    batch, total = [], 0
    for user in recipients:
        batch.append(
            Notification(
                recipient=user,
                kind=Notification.Kind.ANNOUNCEMENT,
                message=f"{announcement.title}: {announcement.message}"[:255],
                url=announcement.url,
            )
        )
        if len(batch) >= 500:
            Notification.objects.bulk_create(batch)
            total += len(batch)
            batch = []
    if batch:
        Notification.objects.bulk_create(batch)
        total += len(batch)
    announcement.sent_at = timezone.now()
    announcement.recipients_count = total
    announcement.save(update_fields=["sent_at", "recipients_count"])
    return total
