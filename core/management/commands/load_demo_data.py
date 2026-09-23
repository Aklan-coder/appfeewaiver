"""
Load clearly-marked DEMO content for local testing.

    python manage.py load_demo_data
    python manage.py remove_demo_data      # removes all of it again

Every demo account has is_demo=True and "(Demo)" in its name. Demo
organisations are fictional and use example.edu / example.org links, so
nothing here can be mistaken for a real opportunity.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from community.models import AchievementType, Comment, Post, PostCategory, Reaction
from moderation.models import Report
from opportunities.models import FundingType, Opportunity, OpportunityType
from resources.models import Resource, ResourceCategory

User = get_user_model()
DEMO_PASSWORD = "demo-password-123"

MEMBERS = [
    ("Amina K. (Demo)", "amina.demo@example.com", "Nigeria", "Computer Science", "masters"),
    ("Tunde O. (Demo)", "tunde.demo@example.com", "Nigeria", "Electrical Engineering", "phd"),
    ("Sarah M. (Demo)", "sarah.demo@example.com", "Kenya", "Public Health", "masters"),
    ("Kebba J. (Demo)", "kebba.demo@example.com", "Gambia", "Data Science", "masters"),
    ("Fatou S. (Demo)", "fatou.demo@example.com", "Senegal", "Economics", "phd"),
    ("Rabi E. (Demo)", "rabi.demo@example.com", "Ghana", "Education", "phd"),
]
TEAM = ("App Fee Waiver Team (Demo)", "team.demo@example.com")


class Command(BaseCommand):
    help = "Load clearly-marked demo users, posts, opportunities and resources (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is False.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to load demo data with DEBUG=False. Use --force if you are sure.")
        if User.objects.filter(is_demo=True).exists():
            raise CommandError("Demo data already exists. Run `python manage.py remove_demo_data` first.")

        now = timezone.now()
        today = timezone.localdate()

        members = []
        for i, (name, email, country, field, degree) in enumerate(MEMBERS):
            user = User.objects.create_user(email=email, password=DEMO_PASSWORD, full_name=name, is_demo=True, email_verified=True)
            User.objects.filter(pk=user.pk).update(date_joined=now - timedelta(days=40 - i * 5))
            profile = user.profile
            profile.country, profile.field_of_study, profile.degree_level = country, field, degree
            profile.bio = "Demo member account used to preview the community."
            profile.save()
            members.append(user)
        team = User.objects.create_user(
            email=TEAM[1], password=DEMO_PASSWORD, full_name=TEAM[0], is_demo=True, email_verified=True
        )
        amina, tunde, sarah, kebba, fatou, rabi = members

        cat = {c.slug: c for c in PostCategory.objects.all()}
        posts_data = [
            (amina, "scholarships", "Fully funded Master's in Germany – application tips?",
             "Has anyone applied for a fully funded Master's in Germany? I'm looking for tips on the motivation letter and on whether universities there offer application fee waivers.", 2, ""),
            (tunde, "cv-sop-advice", "Please review the structure of my CV for PhD applications",
             "I'm applying for PhD programs in Computer Engineering. Should publications come before work experience? I've emailed my CV to the review team as well, but I'd love general advice from the community.", 4, ""),
            (sarah, "application-fee-waivers", "How do I ask a US university for an application fee waiver?",
             "What should I include in an email to a graduate admissions office asking for a fee waiver? Is it better to email the department or the graduate school?", 6, ""),
            (kebba, "application-advice", "Feedback on my Statement of Purpose opening paragraph",
             "I'm applying for a Master's in Data Science. My opening talks about a project I did in my final year. Is it better to start with a story or with my goals?", 9, ""),
            (fatou, "success-stories", "Got admission with an application fee waiver!",
             "Alhamdulillah! I received admission to a PhD program in Economics, and the department waived my application fee after I emailed them. Sharing my timeline: I emailed in October, got the waiver in a week, applied in November and heard back in March. Don't be afraid to ask!", 26, AchievementType.ADMISSION),
            (rabi, "success-stories", "Graduate assistantship offer received",
             "After months of emailing potential supervisors, I received a graduate assistantship covering tuition plus a stipend. Keep going, everyone!", 50, AchievementType.ASSISTANTSHIP),
            (amina, "visa-travel", "Student visa interview: what questions did you get?",
             "My visa interview is next month. For those who've done it recently, what kind of questions were you asked about funding?", 70, ""),
            (sarah, "success-stories", "Scholarship received for my Master's",
             "I'm happy to share that I received a partial scholarship for my Master's in Public Health. The community's SOP feedback really helped.", 90, AchievementType.SCHOLARSHIP),
            (kebba, "general-discussion", "How many universities are you applying to this cycle?",
             "I'm trying to decide between 6 and 10 applications. How did you balance cost, fee waivers and your chances?", 110, ""),
            (tunde, "research-opportunities", "Emailing potential PhD supervisors: when is the best time?",
             "Is it better to email professors before or after submitting an application? And how long should the email be?", 130, ""),
        ]
        posts = []
        for author, slug, title, body, hours_ago, achievement in posts_data:
            post = Post.objects.create(author=author, category=cat[slug], title=title, body=body, achievement_type=achievement)
            Post.objects.filter(pk=post.pk).update(created_at=now - timedelta(hours=hours_ago))
            posts.append(post)

        comments = [
            (0, tunde, "Check the university's international office page. Several German universities don't charge application fees at all, but uni-assist may charge a handling fee."),
            (0, sarah, "Start your motivation letter with why this specific program fits your goals."),
            (1, rabi, "For PhD applications, put research experience and publications near the top."),
            (2, fatou, "I emailed the graduate school directly with a short, polite note explaining my circumstances. It worked!"),
            (2, amina, "Some universities have a fee waiver form on their admissions page, so check there first."),
            (4, amina, "Congratulations! This is so encouraging."),
            (4, kebba, "Congrats! How long did it take them to reply to your waiver request?"),
            (5, sarah, "Well deserved, congratulations!"),
            (9, rabi, "Usually a few months before the deadline. Keep it under 200 words and mention one of their recent papers."),
        ]
        created_comments = []
        for idx, author, body in comments:
            created_comments.append(Comment.objects.create(post=posts[idx], author=author, body=body))
        # A threaded reply
        Comment.objects.create(post=posts[4], author=fatou, parent=created_comments[6], body="About a week. I followed up once after five days.")

        for post, likers in [(posts[4], members), (posts[5], members[:4]), (posts[0], members[1:4]), (posts[2], members[:2])]:
            for user in likers:
                if user.pk != post.author_id:
                    Reaction.objects.get_or_create(user=user, post=post)

        types = {t.slug: t for t in OpportunityType.objects.all()}
        opportunities = [
            ("PhD Application Fee Waiver for International Applicants", "Example State University (Demo)", "United States",
             "application-fee-waivers", "phd", "Any field", FundingType.FEE_WAIVER, 45, Opportunity.Status.VERIFIED, amina),
            ("Fully Funded Master's Scholarship in Engineering", "Demo Technical University", "Germany",
             "scholarships", "masters", "Engineering", FundingType.FULLY_FUNDED, 60, Opportunity.Status.VERIFIED, tunde),
            ("Graduate Research Assistantship in Machine Learning", "Northfield Institute of Technology (Demo)", "Canada",
             "research-assistantships", "phd", "Computer Science", FundingType.STIPEND, 20, Opportunity.Status.VERIFIED, team),
            ("Master's Application Fee Waiver – Public Health", "Lakeside University (Demo)", "United States",
             "application-fee-waivers", "masters", "Public Health", FundingType.FEE_WAIVER, 12, Opportunity.Status.SUBMITTED, sarah),
            ("International Excellence Scholarship", "University of Example (Demo)", "United Kingdom",
             "scholarships", "masters", "Any field", FundingType.PARTIAL, 90, Opportunity.Status.SUBMITTED, kebba),
            ("Doctoral Fellowship in Economics", "Demo Institute for Development Research", "Netherlands",
             "fellowships", "phd", "Economics", FundingType.FULLY_FUNDED, 75, Opportunity.Status.VERIFIED, team),
            ("Teaching Assistantship – Mathematics Department", "Riverbend University (Demo)", "United States",
             "teaching-assistantships", "masters", "Mathematics", FundingType.TUITION, 35, Opportunity.Status.VERIFIED, rabi),
            ("Summer Research Internship for Undergraduates", "Demo Research Foundation", "Switzerland",
             "internships", "undergraduate", "Natural Sciences", FundingType.STIPEND, 28, Opportunity.Status.SUBMITTED, fatou),
            ("Fully Funded PhD Program in Computer Science", "Harbor University (Demo)", "Australia",
             "fully-funded-programs", "phd", "Computer Science", FundingType.FULLY_FUNDED, None, Opportunity.Status.VERIFIED, team),
        ]
        for title, org, country, type_slug, degree, field, funding, days, status, poster in opportunities:
            opp = Opportunity.objects.create(
                title=title,
                organization=org,
                country=country,
                opportunity_type=types[type_slug],
                degree_level=degree,
                field_of_study=field,
                funding_type=funding,
                deadline=today + timedelta(days=days) if days else None,
                deadline_note="" if days else "Rolling admissions",
                description=(
                    "DEMO LISTING – this organisation is fictional and exists only to preview the website. "
                    "In a real listing, this section summarises what the opportunity offers, who it is for and how to apply."
                ),
                eligibility="Demo eligibility text: e.g. international applicants with a relevant degree.",
                official_source_url="https://www.example.edu/demo-official-source",
                application_url="https://www.example.edu/demo-apply",
                posted_by=poster,
                status=status,
            )
            if status == Opportunity.Status.VERIFIED:
                opp.verified_by, opp.verified_at = team, now
                opp.save(update_fields=["verified_by", "verified_at"])

        rcat = {c.slug: c for c in ResourceCategory.objects.all()}
        resources = [
            ("How to Ask for an Application Fee Waiver", "fee-waiver-guides", Resource.Kind.GUIDE, True,
             "A step-by-step approach to requesting a waiver from graduate schools and departments.",
             "Many universities will waive the application fee if you ask politely and explain your situation.\n\n"
             "Start by checking the admissions website for a fee waiver policy or form. If there is none, email the graduate program coordinator.\n\n"
             "- Check the admissions page for an official waiver form\n- Keep your email short and polite\n- Explain briefly why you are requesting a waiver\n- Mention your interest in the specific program\n- Follow up once after a week if you get no reply"),
            ("Statement of Purpose: Structure That Works", "sop-guides", Resource.Kind.GUIDE, True,
             "A simple five-part structure for a clear, focused Statement of Purpose.",
             "A strong SOP answers three questions: why this field, why you, and why this program.\n\n"
             "Open with a specific moment or problem that drew you to the field. Then describe your preparation, research or work, and finish with your goals and why the program fits."),
            ("Academic CV Checklist", "cv-guides", Resource.Kind.CHECKLIST, True,
             "Make sure your academic CV includes everything admissions committees look for.",
             "Use this checklist before sending your CV for review.\n\n"
             "- Contact details (email, city, country)\n- Education with dates and grades\n- Research experience\n- Publications and presentations\n- Work and teaching experience\n- Awards and scholarships\n- Skills (technical and language)\n- References available on request"),
            ("Fee Waiver Request Email Template", "email-templates", Resource.Kind.TEMPLATE, False,
             "A polite, ready-to-adapt email for requesting an application fee waiver.",
             "Subject: Application Fee Waiver Request – [Program Name]\n\nDear [Coordinator's name],\n\n"
             "I am preparing to apply to the [Program Name] for [Term]. I am very interested in [specific reason]. "
             "Due to [brief reason], I would like to ask whether an application fee waiver is available.\n\nThank you for your time.\n\nKind regards,\n[Your name]"),
            ("Graduate Application Timeline", "application-checklists", Resource.Kind.CHECKLIST, True,
             "What to do and when, from 12 months before the deadline.",
             "- 12 months before: research programs and funding\n- 9 months before: prepare for any required tests\n- 6 months before: contact referees and potential supervisors\n- 4 months before: draft your SOP and CV\n- 3 months before: request fee waivers\n- 2 months before: finalise documents\n- 1 month before: submit applications"),
            ("Preparing for Scholarship Interviews", "interview-preparation", Resource.Kind.ARTICLE, False,
             "Common scholarship interview questions and how to prepare.",
             "Interviews test whether your goals are clear and whether you can explain them simply.\n\n"
             "Practise explaining your research or career plan in two minutes, and prepare examples of leadership and impact."),
        ]
        for title, cslug, kind, featured, summary, body in resources:
            Resource.objects.create(
                title=title, category=rcat[cslug], kind=kind, is_featured=featured, summary=summary, body=body, author=team
            )

        Report.objects.create(reporter=kebba, post=posts[8], reason=Report.Reason.DUPLICATE, details="Demo report so the moderation queue has something to show.")

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded: {len(members) + 1} demo users, {len(posts)} posts, {len(opportunities)} opportunities, "
            f"{len(resources)} resources.\nDemo login: {amina.email} / {DEMO_PASSWORD}\n"
            "Remove it any time with: python manage.py remove_demo_data"
        ))
