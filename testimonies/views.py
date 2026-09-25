import hmac

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.utils import paginate

from .models import SuccessType, Testimony
from .sync import maybe_auto_sync, run_sync

FILTERS = [
    ("", "All"),
    (SuccessType.FULLY_FUNDED, "Fully Funded"),
    (SuccessType.SCHOLARSHIP, "Scholarship"),
    (SuccessType.ADMISSION, "Admission"),
    (SuccessType.FEE_WAIVER, "Fee Waiver"),
    (SuccessType.ASSISTANTSHIP, "Assistantship"),
    (SuccessType.FELLOWSHIP, "Fellowship"),
]


def testimony_list(request):
    maybe_auto_sync()
    category = request.GET.get("type", "")
    testimonies = Testimony.objects.published()
    if category in SuccessType.values:
        testimonies = testimonies.filter(success_type=category)
    else:
        category = ""
    return render(
        request,
        "testimonies/list.html",
        {
            "page_obj": paginate(request, testimonies, settings.TESTIMONIES_PER_PAGE),
            "filters": FILTERS,
            "active_type": category,
            "querystring": f"type={category}" if category else "",
        },
    )


@require_http_methods(["GET", "POST"])
def sync_endpoint(request):
    """
    Optional: lets a free external scheduler (e.g. cron-job.org or a GitHub Actions
    schedule) trigger a sync: GET /testimonies/sync/?token=<TESTIMONY_SYNC_TOKEN>
    """
    token = request.GET.get("token") or request.headers.get("X-Sync-Token", "")
    expected = settings.TESTIMONY_SYNC_TOKEN
    if not expected or not hmac.compare_digest(token, expected):
        return HttpResponseForbidden("Invalid token")
    log = run_sync(trigger="endpoint")
    return JsonResponse({"status": log.status, "message": log.message})
