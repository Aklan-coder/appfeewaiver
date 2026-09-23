from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.utils import paginate

from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("actor")
    return render(request, "notifications/list.html", {"page_obj": paginate(request, notifications, 25)})


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    target = notification.url
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    if target and target.startswith(("https://", "http://")):
        return redirect(target)  # admin-written announcement link
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:list")
