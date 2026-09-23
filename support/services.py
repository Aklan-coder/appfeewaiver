"""Expert support content and the pre-filled email templates (mailto: links)."""
from urllib.parse import quote

EXPERT_SERVICES = [
    {
        "key": "scholarship",
        "title": "Scholarship Guidance",
        "icon": "award",
        "description": "Find scholarships that fit your profile, understand eligibility and plan strong applications.",
    },
    {
        "key": "application",
        "title": "University Application Guidance",
        "icon": "school",
        "description": "Step-by-step help with application requirements, portals, documents and timelines.",
    },
    {
        "key": "cv",
        "title": "CV Review",
        "icon": "file-user",
        "description": "Feedback on structure, clarity and how well your academic CV presents your experience.",
    },
    {
        "key": "sop",
        "title": "SOP Review",
        "icon": "file-text",
        "description": "Feedback on your Statement of Purpose or personal statement: story, focus and fit.",
    },
    {
        "key": "selection",
        "title": "University Selection",
        "icon": "map",
        "description": "Build a balanced shortlist of universities and programs based on your goals and budget.",
    },
    {
        "key": "strategy",
        "title": "Application Strategy",
        "icon": "target",
        "description": "Plan your application season: deadlines, fee waivers, funding options and priorities.",
    },
    {
        "key": "general",
        "title": "General Consultation",
        "icon": "chat",
        "description": "Not sure where to start? Talk through your situation and get pointed in the right direction.",
    },
]

APPOINTMENT_TOPICS = [
    "Scholarship Guidance",
    "Application Guidance",
    "CV Review",
    "SOP Review",
    "University Selection",
    "General Consultation",
]

CV_SUBJECT = "CV Review Request – App Fee Waiver"
SOP_SUBJECT = "SOP Review Request – App Fee Waiver"
APPOINTMENT_SUBJECT = "Appointment Request – App Fee Waiver"

REVIEW_BODY = """Hello App Fee Waiver Team,

I would like to request a review of my {document}. My details are below.

Full name:
Target degree:
Field of study:
Target university/universities:
Target country:
Application deadline:
Type of feedback requested:

I have attached my {document} as a PDF.

Thank you,
"""

APPOINTMENT_BODY = """Hello App Fee Waiver Team,

I would like to request an appointment.

Name:
Country/Timezone:
Type of Support: {topic}
Preferred Date:
Preferred Time:
Alternative Date/Time:

Please briefly explain what you need help with:


Thank you,
"""


def mailto(address, subject, body):
    return f"mailto:{address}?subject={quote(subject)}&body={quote(body)}"


def cv_mailto(site_settings):
    return mailto(site_settings.cv_review, CV_SUBJECT, REVIEW_BODY.format(document="CV"))


def sop_mailto(site_settings):
    return mailto(site_settings.sop_review, SOP_SUBJECT, REVIEW_BODY.format(document="Statement of Purpose (SOP)"))


def appointment_mailto(site_settings, topic=""):
    return mailto(site_settings.appointment, APPOINTMENT_SUBJECT, APPOINTMENT_BODY.format(topic=topic))
