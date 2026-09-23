def notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    unread = user.notifications.filter(is_read=False)
    return {
        "unread_notifications_count": unread.count(),
        "recent_notifications": user.notifications.select_related("actor")[:6],
    }
