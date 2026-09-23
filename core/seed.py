"""
Reference data the platform needs to work: categories, opportunity types,
the Moderator role and the Site Settings row. This is NOT demo content and
runs automatically after every `migrate` (it never overwrites admin edits).
"""
from django.apps import apps as django_apps

POST_CATEGORIES = [
    ("Scholarships", "scholarships"),
    ("Application Fee Waivers", "application-fee-waivers"),
    ("Graduate Admissions", "graduate-admissions"),
    ("Undergraduate Admissions", "undergraduate-admissions"),
    ("Assistantships", "assistantships"),
    ("Fellowships", "fellowships"),
    ("Internships", "internships"),
    ("Research Opportunities", "research-opportunities"),
    ("Application Advice", "application-advice"),
    ("Visa & Travel", "visa-travel"),
    ("CV/SOP Advice", "cv-sop-advice"),
    ("Success Stories", "success-stories"),
    ("General Discussion", "general-discussion"),
]

OPPORTUNITY_TYPES = [
    ("Scholarship", "scholarships", "SCHOLARSHIP"),
    ("Application Fee Waiver", "application-fee-waivers", "FEE WAIVER"),
    ("Fully Funded Program", "fully-funded-programs", "FULLY FUNDED"),
    ("Graduate Assistantship", "graduate-assistantships", "ASSISTANTSHIP"),
    ("Research Assistantship", "research-assistantships", "RESEARCH ASSISTANTSHIP"),
    ("Teaching Assistantship", "teaching-assistantships", "TEACHING ASSISTANTSHIP"),
    ("Fellowship", "fellowships", "FELLOWSHIP"),
    ("Internship", "internships", "INTERNSHIP"),
    ("Research Opportunity", "research-opportunities", "RESEARCH"),
]

RESOURCE_CATEGORIES = [
    ("Scholarship Guides", "scholarship-guides"),
    ("Application Fee Waiver Guides", "fee-waiver-guides"),
    ("CV Guides", "cv-guides"),
    ("SOP Guides", "sop-guides"),
    ("Personal Statement Guides", "personal-statement-guides"),
    ("Email Templates", "email-templates"),
    ("Graduate Application Guides", "graduate-application-guides"),
    ("Undergraduate Application Guides", "undergraduate-application-guides"),
    ("Interview Preparation", "interview-preparation"),
    ("Funding Guides", "funding-guides"),
    ("Application Checklists", "application-checklists"),
]

MODERATOR_PERMISSIONS = [
    # (app_label, codename)
    ("moderation", "review_report"),
    ("moderation", "view_report"),
    ("moderation", "change_report"),
    ("opportunities", "verify_opportunity"),
    ("opportunities", "view_opportunity"),
    ("opportunities", "change_opportunity"),
    ("community", "view_post"),
    ("community", "change_post"),
    ("community", "view_comment"),
    ("community", "change_comment"),
    ("resources", "view_resource"),
]


def seed_reference_data(**kwargs):
    from django.contrib.auth.management import create_permissions
    from django.contrib.auth.models import Group, Permission

    PostCategory = django_apps.get_model("community", "PostCategory")
    OpportunityType = django_apps.get_model("opportunities", "OpportunityType")
    ResourceCategory = django_apps.get_model("resources", "ResourceCategory")
    SiteSettings = django_apps.get_model("core", "SiteSettings")

    from django.db import connection

    existing = set(connection.introspection.table_names())
    needed = {m._meta.db_table for m in (PostCategory, OpportunityType, ResourceCategory, SiteSettings)}
    if not needed.issubset(existing):
        return  # migrations for these apps haven't been applied yet

    for order, (name, slug) in enumerate(POST_CATEGORIES):
        PostCategory.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})

    for order, (name, slug, label) in enumerate(OPPORTUNITY_TYPES):
        OpportunityType.objects.get_or_create(slug=slug, defaults={"name": name, "short_label": label, "order": order})

    for order, (name, slug) in enumerate(RESOURCE_CATEGORIES):
        ResourceCategory.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})

    SiteSettings.objects.get_or_create(pk=1, defaults={"primary_email": "appfeewaiver@gmail.com"})

    # Make sure every app's permissions exist before assigning them.
    for app_config in django_apps.get_app_configs():
        create_permissions(app_config, verbosity=0)

    group, _ = Group.objects.get_or_create(name="Moderator")
    for app_label, codename in MODERATOR_PERMISSIONS:
        perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        if perm:
            group.permissions.add(perm)
