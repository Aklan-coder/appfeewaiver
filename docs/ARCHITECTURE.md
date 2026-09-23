# App Fee Waiver: Version 1 plan

This document covers the planning sections requested in the brief (A–H). The code in this repository implements it.

---

## What the mockup and logo told us

**Logo:** a graduation cap over an open-box "shield" shape with a navy→emerald gradient; the wordmark "App Fee" in deep navy (`#0A172D`) and "Waiver" in emerald (`#13A77A`), with the tagline *Scholarships • Applications • Opportunities* in slate. The site's palette comes straight from it:

| Token | Hex | Used for |
|---|---|---|
| `navy-900` | `#0A172D` | Text, hero background, dark buttons |
| `brand-500` | `#13A77A` | Accents, "Waiver" highlight, bright buttons on navy |
| `brand-700` | `#0B7152` | Primary buttons and links (meets WCAG AA contrast with white) |
| teal / slate / white | – | Secondary accents, muted text, cards |
| `#F5F7FA` | – | Page background (very light grey) |

**Mockup:** a dashboard-style homepage, not a marketing landing page:
- sticky white header with logo, six nav links (active one underlined in green), search box, bell, *Log In* / *Join Now*
- a dark navy hero card with "App Fee **Waiver**", headline, two CTAs, member stats, and a translucent checklist panel on the right
- a row of eight pastel quick-action tiles
- a *Latest Posts* feed card with category tabs and a sort dropdown
- a middle sidebar (New to App Fee Waiver?, Post your CV/SOP, Book an Appointment, Quick Resources, Community Stats)
- a right sidebar (Trending Opportunities with deadlines, Top Contributors, Join Our Groups)

Corrections applied: **10,000+ → configurable "2,000+"**; closed-group/support-group counts (not in the database) were dropped; CV/SOP "upload" became **email**; "Trending" became **Upcoming Deadlines** (real, computable); real scholarship names with dates were replaced with honest data from the database.

---

## A. Proposed architecture

```
Browser ──HTTPS──▶ Django (Gunicorn) ──▶ PostgreSQL
   │                  │   ├── Django templates + Tailwind CSS (server-rendered HTML)
   │                  │   ├── Django auth (email login, hashed passwords, CSRF)
   │                  │   ├── Django Admin (full management) + branded dashboard & moderation queue
   │                  │   └── WhiteNoise serves /static/ (CSS, JS, logo) from the same server
   │                  └── SMTP (optional, free) for verification / password-reset emails
   └── mailto: links ──▶ member's own email app ──▶ App Fee Waiver inbox   (CVs, SOPs, appointments)
```

- **Server-rendered Django** (no React). Each page is one request returning HTML. This keeps it fast, SEO-friendly and simple to maintain.
- **Alpine.js** (from the jsDelivr CDN) adds small interactions: dropdowns, the mobile menu, tabs, the report dialog, reply boxes and the checklist. **`static/js/app.js`** (about 100 lines, no framework) makes like/save/share instant with `fetch`. Every one of these still works as a normal form without JavaScript.
- **No REST API** in V1: nothing needs it yet. The two JSON responses (like/save toggles) are plain Django views.
- **Search** uses portable database queries (every word must match; synonyms like *US → United States*, *Master's → master*). It works the same on SQLite and PostgreSQL and can later be upgraded to PostgreSQL full-text search.
- **Rate limiting and anti-spam** use Django's cache plus a hidden honeypot field. No external service.
- **Notifications** are database rows shown in the header bell and on `/notifications/`. No push service.
- **Site Settings** is a single database row edited in Django Admin; every email button reads from it.

## B. Django project structure

```
appfeewaiver/                  ← repository root (open this in VS Code)
├── manage.py
├── requirements.txt           Django, dj-database-url, python-dotenv, whitenoise, Pillow, psycopg, gunicorn
├── .env.example  .gitignore   build.sh  render.yaml  package.json  tailwind.config.js
├── appfeewaiver/              settings.py · urls.py · wsgi.py · asgi.py
├── core/                      home, about, contact, policies, search, dashboard, SiteSettings,
│   ├── seed.py                reference data (categories, types, Moderator group) created after migrate
│   ├── templatetags/afw.py    avatar, icons, pagination/filter URL helpers
│   └── management/commands/   load_demo_data · remove_demo_data · create_moderator
├── accounts/                  User (email login), Profile, sign-up, login, password, profiles, saved items
├── community/                 PostCategory, Post, Comment, Reaction, SavedPost, success stories
├── opportunities/             OpportunityType, Opportunity, SavedOpportunity, filters, submit, review
├── resources/                 ResourceCategory, Resource
├── support/                   Expert Support, CV & SOP Review, appointments (mailto templates in services.py)
├── notifications/             Notification, Announcement, notify() helper
├── moderation/                Report, moderation queue, resolve actions
├── templates/                 base.html · partials/ · one folder per app
├── static/                    css/ (tailwind.css, components.css) · js/ · img/ (logo, favicon, OG image)
└── docs/                      ARCHITECTURE.md · DEPLOYMENT.md · reference/homepage-mockup.png
```

## C. Database schema

```
User ─1:1─ Profile
 │ (email unique, full_name, handle slug, email_verified, warning_count, suspended_until, is_demo)
 │
 ├─< Post >─ PostCategory            Post: title, slug (unique), body, external_link, achievement_type,
 │    │                                     status (published/removed), is_pinned, created/updated/edited
 │    ├─< Comment (parent → Comment)  one level of replies; status for moderation
 │    ├─< Reaction  (unique user+post)
 │    └─< SavedPost (unique user+post)
 │
 ├─< Opportunity >─ OpportunityType   Opportunity: title, slug "organisation-title", organization, country,
 │    │                                degree_level, field_of_study, funding_type, deadline / deadline_note,
 │    │                                description, eligibility, additional_info, official_source_url,
 │    │                                application_url, status (Community Submitted / Verified / Rejected),
 │    │                                posted_by, verified_by, verified_at, review_note
 │    └─< SavedOpportunity (unique user+opportunity)
 │
 ├─< Report ─ (Post XOR Comment)      reason, details, status (open/dismissed/actioned), resolved_by/at, note
 │                                     DB constraints: exactly one target; one open report per member per item
 ├─< Notification                     kind, message, url, is_read, actor
 │
Resource >─ ResourceCategory           title, slug, kind (article/guide/link/template/checklist), summary,
                                       body, external_url, is_published, is_featured, published_at
Announcement                           admin action "Send to all members" → Notifications
SiteSettings (single row)              primary/contact/cv/sop/appointment/support/partnership emails,
                                       member_count_display, community group link, announcement banner
```

Indexes cover the hot queries: feed (`status, -created_at`, per category), opportunity listing (`status`, type, country, degree, deadline) and unread notifications (`recipient, is_read, -created_at`). All models have timestamps; posts, opportunities and resources have readable unique slugs.

## D. User roles

| | Member | Moderator | Administrator |
|---|---|---|---|
| Create/edit/delete own posts & comments, like, save, share | ✓ | ✓ | ✓ |
| Submit opportunities, report content | ✓ | ✓ | ✓ |
| Moderation queue: dismiss reports, remove/restore content | | ✓ | ✓ |
| Warn or suspend members (7 days) | | ✓ | ✓ |
| Verify / reject / un-verify opportunities | | ✓ | ✓ |
| Dashboard with platform statistics | | ✓ | ✓ |
| Django Admin | | limited (group permissions) | full |
| Site Settings, categories, resources, roles, announcements | | | ✓ |

Implementation: members are ordinary accounts; **Moderator** is a Django **Group** created automatically with specific permissions (`review_report`, `verify_opportunity`, change posts/comments). Administrators are superusers. Suspended members can browse but not post (`User.can_participate`).

## E. Page map

```
/                                   Home (hero, checklist, quick actions, feed, sidebars, opportunities, stories, resources, CTA)
├── /community/                     Feed: Latest · Popular · Most Discussed · Unanswered, categories, search
│   ├── /community/new/             Create post (?category=… preselects)
│   ├── /community/<slug>/          Post: comments + replies, like, save, share, report, edit/delete
│   └── /community/success-stories/ Success stories (filter by achievement)
├── /opportunities/                 Filters: type, country, degree, funding, field, deadline, verified, search
│   ├── /opportunities/type/<type>/ e.g. /opportunities/type/scholarships/
│   ├── /opportunities/submit/      Submit an Opportunity → "Community Submitted"
│   └── /opportunities/<org-title>/ Detail: official links, save, share, moderator review panel
├── /resources/  → /resources/<slug>/
├── /support/                       Expert Support (7 service types)
│   ├── /support/cv-sop-review/     Submit CV / Submit SOP (mailto:)
│   └── /support/appointment/       Request Appointment (mailto:)
├── /search/?q=                     Global search with type labels
├── /about/ /contact/ /privacy/ /terms/ /community-guidelines/ /disclaimer/
├── /accounts/join/ · login/ · logout/ · password/reset|change/ · verify/
│   ├── /accounts/members/<handle>/ Public profile (posts, contributions, success stories)
│   ├── /accounts/profile/edit/     Profile + privacy switches
│   ├── /accounts/my-posts/ · saved/ · settings/
├── /notifications/
├── /dashboard/  /moderation/       Moderators & admins
├── /admin/                         Django Admin
└── /sitemap.xml  /robots.txt
```

## F. Homepage breakdown (how the mockup is reproduced)

| Mockup element | Implementation |
|---|---|
| Sticky header | `partials/header.html`: logo, six links with green active underline, search, bell (dropdown with latest notifications), Log In / Join Now → avatar menu (My Profile, My Posts, Saved Opportunities, Settings, Log Out). Hamburger menu below 1280 px. |
| Navy hero with checklist panel | Hero card with the brand word treatment, headline, *Join the Community* / *Post a Question*, **2,000+ Members** plus database stats (posts, scholarships, fee waivers, countries) shown only when above zero. The glass panel is **Your Application Checklist**; ticks are remembered in the member's browser. |
| Eight pastel tiles | Quick actions: Find Scholarships, Application Fee Waivers, Ask a Question, Submit an Opportunity, CV & SOP Review, Request Appointment, Resources, Success Stories. |
| Latest Posts card | "Latest from the Community": category tabs, sort dropdown, post rows with avatar, category badge, time, comments, likes, save, share, report; *View All Community Posts*. |
| Middle sidebar | New to App Fee Waiver? (or Welcome back), CV/SOP review, Book an Appointment (shows the configured email), Quick Resources (featured), Community Stats. |
| Right sidebar | Upcoming Deadlines (real deadlines), Top Contributors (by post count), Join Our Group (only if a link is set in Site Settings). |
| Below the fold | What You Can Do Here (7 features), Latest Opportunities (tabs: All/Scholarships/Fee Waivers/Assistantships/Fellowships), Success Stories, Guides & Resources, Join CTA, footer. |

Layout: three columns from 1280 px (`main | 290 px | 265 px`), two columns from 1024 px, one column on phones; nothing scrolls sideways at 360 px.

## G. Free deployment plan

| Piece | Where | Cost |
|---|---|---|
| Source code | **GitHub** (private or public repo) | Free |
| Django app | **Render** free web service (Gunicorn). Custom domains supported. Sleeps after 15 min idle; the first visit after that takes about a minute | Free |
| PostgreSQL | **Neon** free plan (0.5 GB storage, no expiry, sleeps when idle). Avoid Render's free Postgres: it's deleted after 30 days | Free |
| Static files | **WhiteNoise** inside the Django app (compressed, cache-busted) | Free |
| Emails (optional) | Any SMTP with a free tier, e.g. a Gmail account with an App Password | Free |
| CVs / SOPs | **Not stored.** Members email them to the configured inbox | Free |
| Domain | Your registrar → CNAME to Render | Your only cost |

Upgrade path when the community grows: Render paid instance (no sleep), Neon paid plan or any managed Postgres, object storage for profile photos, a transactional email provider. All of these are settings changes, not code rewrites. Step-by-step instructions are in [`DEPLOYMENT.md`](DEPLOYMENT.md).

## H. Implementation phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup, settings, environment variables, apps | ✅ |
| 2 | Database models, indexes, constraints, reference data | ✅ |
| 3 | Authentication: email sign-up/login, verification, reset/change password | ✅ |
| 4 | Base layout, header, footer, design system (Tailwind + components) | ✅ |
| 5 | Homepage (mockup layout) | ✅ |
| 6–8 | Community feed, posts, comments & replies, likes, saves, share, filters | ✅ |
| 9–10 | Opportunities, filters, submissions, verification | ✅ |
| 11–12 | Global search, saved opportunities | ✅ |
| 13–15 | CV & SOP email page, Expert Support, appointment emails | ✅ |
| 16–18 | Resources, profiles with privacy switches, success stories | ✅ |
| 19–21 | Notifications, moderation (reports, warn/suspend), dashboard, admin configuration | ✅ |
| 22–24 | Mobile responsiveness, security settings, automated tests (29) | ✅ |
| 25 | Deployment preparation (build script, Render blueprint, docs) | ✅ |
| Later | Direct uploads, scheduling, AI matching, push notifications, premium features | Not built (by design) |
