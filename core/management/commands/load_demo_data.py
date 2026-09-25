"""
Clearly-marked DEMO content for local testing only.

    python manage.py load_demo_data
    python manage.py remove_demo_data
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from content.models import Post, PostCategory, Resource, ResourceCategory
from registrations.models import WhatsAppGroup
from testimonies.models import SuccessType, Testimony

DEMO_LINK_PREFIX = "https://chat.whatsapp.com/DEMO"

DEMO_TESTIMONIES = [
    ("Aisha S. (Demo)", "Master's in Data Science", "Germany", SuccessType.FULLY_FUNDED,
     "Demo testimony: I received a fully funded Master's offer after finding the opportunity through the App Fee Waiver WhatsApp community."),
    ("Daniel K. (Demo)", "PhD in Computer Engineering", "United States", SuccessType.ADMISSION,
     "Demo testimony: I got my PhD admission with a full assistantship. The fee waiver tips shared in the group helped a lot."),
    ("Fatou J. (Demo)", "Master's in Public Health", "Canada", SuccessType.FEE_WAIVER,
     "Demo testimony: I got application fee waivers for three universities through information shared in the community."),
    ("Ibrahim T. (Demo)", "Master's in Artificial Intelligence", "United Kingdom", SuccessType.SCHOLARSHIP,
     "Demo testimony: I received a scholarship offer for my Master's. The opportunities shared in the WhatsApp group are very helpful."),
    ("Grace O. (Demo)", "PhD in Chemistry", "Canada", SuccessType.ASSISTANTSHIP,
     "Demo testimony: A research assistantship covered my tuition and stipend. Thank you to everyone who answered my questions."),
]

DEMO_POSTS = [
    ("Demo: How to Get Application Fee Waivers for US Graduate Programs", PostCategory.FEE_WAIVER, 30),
    ("Demo: Fully Funded Master's Scholarships in Europe (2027 Intake)", PostCategory.SCHOLARSHIP, 45),
    ("Demo: Summer Research Internships for International Students", PostCategory.INTERNSHIP, 20),
    ("Demo: Early-Career Research Fellowships Now Open", PostCategory.FELLOWSHIP, None),
]
DEMO_BODY = (
    "This is demo content for testing the blog. Replace it with a real post in Admin → Blog posts.\n\n"
    "Write a short introduction, who can apply, what is covered, and how to apply. "
    "Leave a blank line between paragraphs.\n\nOfficial page: https://example.com"
)
DEMO_RESOURCES = [
    ("Demo CV format (graduate applications)", ResourceCategory.CV, "A clean one-page academic CV layout."),
    ("Demo statement of purpose sample", ResourceCategory.SOP, "Structure: motivation, background, research fit, goals."),
    ("Demo SOP outline worksheet", ResourceCategory.SOP, "Plan each paragraph before you write."),
]


class Command(BaseCommand):
    help = "Load demo WhatsApp groups and demo testimonies (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is False.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to load demo data with DEBUG=False. Use --force if you are sure.")
        # Each kind of demo data is only added if it isn't there yet, so re-running is safe.
        if not WhatsAppGroup.objects.exists():
            WhatsAppGroup.objects.create(name="Community Group 1 (Demo)", invite_link=f"{DEMO_LINK_PREFIX}GROUP1", order=1)
            WhatsAppGroup.objects.create(name="Community Group 2 (Demo)", invite_link=f"{DEMO_LINK_PREFIX}GROUP2", order=2)
        now = timezone.now()
        for i, (name, program, country, kind, text) in enumerate(
            [] if Testimony.objects.filter(is_demo=True).exists() else DEMO_TESTIMONIES
        ):
            Testimony.objects.create(
                name=name, program=program, country=country, success_type=kind, testimony=text,
                submitted_at=now - timedelta(days=5 * i + 3), is_demo=True, published=True,
            )
        today = now.date()
        for i, (title, category, days_to_deadline) in enumerate(
            [] if Post.objects.filter(is_demo=True).exists() else DEMO_POSTS
        ):
            Post.objects.create(
                title=title, slug=f"demo-post-{i + 1}", category=category, body=DEMO_BODY, is_demo=True,
                published_at=now - timedelta(days=2 * i + 1),
                deadline=today + timedelta(days=days_to_deadline) if days_to_deadline else None,
            )
        for i, (title, category, description) in enumerate(
            [] if Resource.objects.filter(is_demo=True).exists() else DEMO_RESOURCES
        ):
            Resource.objects.create(
                title=title, category=category, description=description, order=i, is_demo=True,
                link="https://example.com/demo-template",
            )
        self.stdout.write(self.style.SUCCESS(
            "Demo data ready: WhatsApp groups, testimonies, blog posts and resources (anything missing was added). "
            "Remove them with: python manage.py remove_demo_data"
        ))
