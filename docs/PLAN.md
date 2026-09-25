# App Fee Waiver: plan and key decisions

## 1. What does the site do?
It does two things:
- It registers students for the WhatsApp community and emails them the invite link.
- It shows approved funding testimonies.

Everything else from the forum version was removed: posts, comments, member accounts, opportunities,
resources, CV/SOP review, appointments, notifications and moderation. The WhatsApp community itself
is self-run by members.

## 2. What happens to the old data?
Nothing is deleted automatically. The new migrations only:
- add the new tables (registrations, WhatsApp groups, testimonies, sync logs);
- adjust the site settings table.

The old tables stay in the database, unused (`community_*`, `opportunities_*`, `resources_*`,
`notifications_*`, `moderation_*`, `accounts_profile`). Admin users keep working.
`python manage.py drop_legacy_tables` lists the old tables; running it with `--confirm` deletes them,
and only then, when you decide to.

## 3. How is the WhatsApp link kept private?
The links are stored only in the database, in the `WhatsAppGroup` table, and are edited in Admin.
They appear only in the welcome email to the address that registered. They are never in the HTML,
the JavaScript or the form response. The success message is the same for new and repeat emails,
so nobody can check who has registered.

## 4. How are people split between the two groups?
Each new registration goes to the active group with the **fewest** people (ties go to the lower "order").
In practice that alternates Group 1 → Group 2 → Group 1…

Groups that are switched off, or that have reached their optional capacity, are skipped.
A third group added in Admin joins the rotation automatically.

Admins can move people with an action, which also emails them the new link.

## 5. What if someone registers twice?
There is no second row. Their "last requested" time is updated and the link is re-sent,
unless it was sent in the last 10 minutes; that cooldown stops the form being used to flood an inbox.

## 6. How are emails sent for free?
Render's free plan blocks SMTP, so emails go through **Brevo's HTTPS API** (free, 300 emails/day).
No extra Python package is needed.

Every attempt is recorded: sent/not sent, time, attempts and the error. Failures show on the dashboard,
and **Resend WhatsApp email** retries them.

## 7. How do testimonies get from Google Forms to the site?
The flow is Form → Sheet → admin types **YES** in "Approved" → a small Apps Script web app returns
only approved rows, protected by a secret token → Django imports them.

- No Google API keys or service accounts are needed.
- Rows without publishing permission are skipped.
- Rows are matched by a stable ID, so re-syncing never creates duplicates.
- A sync never deletes anything.
- Testimonies edited in Admin are protected from being overwritten.

## 8. How often does it sync, with no paid scheduler?
The site checks automatically when it gets visitors, if the interval has passed (60 minutes by default).
The check runs in the background, so visitors never wait. You can also:
- click **Sync now** in Admin;
- run `python manage.py sync_testimonies`;
- point a free external cron (e.g. cron-job.org) at `/testimonies/sync/?token=…`.

Render's own cron jobs are paid, so they're not used.

## 9. What does the admin get?
A branded dashboard with:
- total registrations, the last 7 days, published and unpublished testimonies, and email failures;
- per-group counts and the last sync.

Plus:
- registrations with search, filters, CSV export, resend and move;
- groups with editable link, active flag, capacity and order;
- testimonies with publish, unpublish, feature and edit;
- sync logs;
- a single **Site settings** page.

## 10. How is it protected against abuse?
- CSRF protection on forms.
- Registrations are rate limited (6 per hour per IP), with a hidden honeypot field for bots.
- Server-side validation of every field.
- No public sign-up of any kind.
- Testimony emails are never displayed.
- Security headers and HTTPS once `DEBUG=False`.
- All secrets are in environment variables only.

## 11. Mobile and performance
The layout is designed mobile-first and checked at 320–1536 px with no horizontal scrolling.

- It has a hamburger menu and a full-width form.
- Testimonies show as a swipeable row on phones.
- The JavaScript is small and framework-free: the form, the menu and photo fallbacks. The site also works without it.
- Fonts are self-hosted, the CSS is precompiled, and images are WebP and responsive.

## 12. What does it cost?
Nothing beyond the domain:
- Render free web service;
- Neon free Postgres;
- Brevo free (a small "Sent with Brevo" footer in emails);
- Google Forms, Sheets and Apps Script (free).

Limits to know:
- Render's free service sleeps after ~15 minutes idle, so the first visit takes a few seconds.
- Brevo allows 300 emails a day.
