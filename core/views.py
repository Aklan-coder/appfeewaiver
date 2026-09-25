from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from registrations.forms import RegistrationForm
from content.models import Post
from testimonies.models import Testimony
from testimonies.sync import maybe_auto_sync

from .models import SiteSettings


def faq_items(site):
    items = [
        (
            "How do I join the WhatsApp community?",
            "Click “Join the Community”, fill in the short form and we'll send the current community link to your email.",
        ),
        (
            "When will I receive the group link?",
            "Right after you register, the system emails you the link. If you can't see it within a few minutes, "
            "check your spam/junk folder.",
        ),
    ]
    if site.community_free_answer.strip():
        items.append(("Is the community free?", site.community_free_answer.strip()))
    items += [
        (
            "What opportunities are shared in the group?",
            "Scholarships, application fee waivers, admissions information, assistantships, fellowships and other "
            "relevant opportunities.",
        ),
        (
            "Can I share an opportunity?",
            "Yes. The community is run by its members: once you've joined, you can share useful opportunities and "
            "help others inside the WhatsApp community.",
        ),
        (
            "How do I submit my success story?",
            "Got funded, admitted or a fee waiver? Use the “Share Your Story” button on the Funding Testimonies "
            "page to fill in our testimony form. Approved stories appear on that page.",
        ),
    ]
    return items


def home(request, registration_form=None):
    maybe_auto_sync()
    site = SiteSettings.load()
    context = {
        "join_form": registration_form or RegistrationForm(),
        "joined": request.GET.get("joined") == "1" and registration_form is None,
        # Open the join pop-up straight away after a no-JavaScript submit (success or errors).
        "open_join": request.GET.get("joined") == "1" or registration_form is not None,
        "testimonies": list(Testimony.objects.published()[:12]),
        "latest_posts": Post.objects.published()[:3],
        "faqs": faq_items(site),
    }
    status = 400 if registration_form is not None else 200
    return render(request, "core/home.html", context, status=status)


def privacy(request):
    return render(request, "core/privacy.html")


@require_GET
def robots_txt(request):
    lines = ["User-agent: *", "Disallow: /admin/", f"Sitemap: {settings.SITE_URL}/sitemap.xml"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)
