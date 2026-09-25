# App Fee Waiver

A simple, mobile-first website with two jobs:

1. **Join the WhatsApp community.** Students register (name, email, country, level, field of study).
   The registration is saved and a welcome email automatically sends them the WhatsApp invite link.
   The link is never shown on the website.
2. **Funding Testimonies.** Members submit their success story through a Google Form. You approve
   it in the Google Sheet (type YES) and it appears on the website automatically.

Built with Django 5.1 + PostgreSQL + Tailwind CSS. It runs on free services: Render, Neon, Brevo
and Google Sheets.

- Deploying: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Welcome emails (Brevo): [docs/EMAIL_SETUP.md](docs/EMAIL_SETUP.md)
- Testimonies from Google Form/Sheet: [docs/GOOGLE_SHEET_SETUP.md](docs/GOOGLE_SHEET_SETUP.md)
- How it's designed, and why: [docs/PLAN.md](docs/PLAN.md)

---

## 1. Run it on your computer (VS Code, Windows)

In the VS Code terminal, inside the project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py load_demo_data      # optional: sample groups + clearly-marked demo testimonies
python manage.py runserver
```

Open http://127.0.0.1:8000 (the site) and http://127.0.0.1:8000/admin/ (the dashboard).

(macOS/Linux: `source .venv/bin/activate` and `cp .env.example .env`.)

With `EMAIL_PROVIDER=console` in `.env`, the welcome email (with the link) is printed in the
terminal, so you can test registrations without sending real emails.

## 2. Updating from the old (forum) version

1. **Back up first:** copy your project folder somewhere safe.
2. In your project folder, **delete everything except** `.venv`, `.env` and `.git`
   (the old `community`, `opportunities`, `resources`, `support`, `notifications` and `moderation`
   folders must be removed, not just overwritten).
3. Copy the contents of this new version into the folder.
4. Run:
   ```powershell
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py test
   git add -A
   git commit -m "Rebuild as single-page registration + testimonies site"
   git push
   ```
5. Follow "Updating the existing live site" in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
   (new Render environment variables, then add your WhatsApp groups in Admin).

**No old data is deleted by the update.** The old forum tables stay in the database, unused.
`python manage.py drop_legacy_tables` lists them, and `--confirm` removes them when you're ready.

## 3. The admin dashboard (`/admin/`)

- **Dashboard:** total registrations, last 7 days, published/unpublished testimonies, email failures, group counts.
- **Registrations:** search by name or email; filter by country, level, group, date and link-sent status.
  Actions: **Resend WhatsApp email**, **Export to CSV**, **Move selected to <group> and email them the new link**.
  You can also change a person's group directly in the list (that alone sends no email).
- **WhatsApp groups:** change an invite link (the next emails use it immediately), switch a group
  on/off, set a capacity, and see how many people each group has. Add a 3rd or 4th group anytime: no code changes needed.
- **Testimonies:** publish/unpublish, feature (shown first), edit, and "Sync from Google Sheet now".
- **Sync logs:** every sync, with results or errors.
- **Blog posts:** Admin → Blog posts → Add. Write a title, pick a category (Scholarships, Fee Waivers,
  Fellowships, Internships…), and write the post as plain text with a blank line between paragraphs.
  Deadline, official link and cover image are optional. The 3 newest posts appear in the "Latest
  Opportunities" card on the home page. Untick *Published* to keep a draft (admins can still preview it).
- **Resources (CV & SOP formats):** put the file in Google Drive or Google Docs, click *Share → Anyone
  with the link → Viewer*, copy the link, then Admin → Resources → Add and paste it. Files aren't uploaded
  to the website because Render's free plan deletes uploaded files on every deploy.
- **Site settings:** member count shown on the site, contact email, registration on/off, announcement bar,
  testimony form + sync URLs, the "Is the community free?" answer, and social links.

Only accounts you create with `createsuperuser` (or add in Admin → Users) can log in. There is no public sign-up.

## 4. Demo data

`python manage.py load_demo_data` adds 2 groups with fake `DEMO` links and 5 testimonies whose names end
in "(Demo)" with the text "Demo testimony:". They are labelled DEMO on the site and excluded from dashboard stats.
Remove them with `python manage.py remove_demo_data`. The command refuses to run when `DEBUG=False`.

## 5. Tests

```powershell
python manage.py test
```
The tests cover:
- registration, validation, duplicates and cooldown;
- that the link is emailed and never appears in pages;
- balanced group assignment, and skipping inactive or full groups;
- email failures and resends;
- the Google Sheet import (approval, consent, no duplicates, admin edits kept, nothing deleted);
- the sync endpoint's token check, the dashboard numbers and the admin actions.

## 6. Changing the design (Tailwind CSS)

The compiled CSS is in `static/css/tailwind.css`. Component styles are in `static/css/components.css`.
If you add new Tailwind classes to templates, rebuild the CSS with the standalone Tailwind CLI or Node:

```bash
npm install
npm run build:css
```
Quick alternative while experimenting: set `TAILWIND_USE_CDN=True` in `.env` (development only).

## 7. Project structure

```
appfeewaiver/      settings and URLs
core/              home page, privacy page, site settings, branded admin dashboard, commands
registrations/     registration form, WhatsApp groups, welcome email, admin actions
testimonies/       testimonies page, Google Sheet sync, admin
content/           blog posts and resources (CV/SOP formats)
accounts/          admin user accounts (email login). Old profile table kept for existing data
templates/         HTML (base, home, testimonies, emails, admin)
static/            CSS, JS (small, no framework), fonts, images
docs/              deployment, email, Google Sheet guides + Apps Script
design/reference/  the approved mockup and original images
```

## 8. Useful commands

| Command | What it does |
|---|---|
| `python manage.py sync_testimonies` | Import approved testimonies from the Google Sheet now |
| `python manage.py load_demo_data` / `remove_demo_data` | Add or remove sample data (local only) |
| `python manage.py drop_legacy_tables [--confirm]` | List (or delete) the old forum tables |
| `python manage.py createsuperuser` | Create an admin login |
