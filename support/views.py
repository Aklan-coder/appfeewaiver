from django.shortcuts import render

from core.models import SiteSettings

from . import services


def cv_sop_review(request):
    site = SiteSettings.load()
    return render(
        request,
        "support/cv_sop_review.html",
        {
            "cv_mailto": services.cv_mailto(site),
            "sop_mailto": services.sop_mailto(site),
            "cv_subject": services.CV_SUBJECT,
            "sop_subject": services.SOP_SUBJECT,
        },
    )


def expert_support(request):
    return render(request, "support/expert_support.html", {"services": services.EXPERT_SERVICES})


def appointment(request):
    site = SiteSettings.load()
    topics = [
        {"name": topic, "mailto": services.appointment_mailto(site, topic)} for topic in services.APPOINTMENT_TOPICS
    ]
    return render(
        request,
        "support/appointment.html",
        {
            "topics": topics,
            "default_mailto": services.appointment_mailto(site),
            "subject": services.APPOINTMENT_SUBJECT,
        },
    )
