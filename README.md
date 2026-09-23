# App Fee Waiver

**Scholarships • Applications • Opportunities**

A community platform where students discover scholarships, application fee waivers and funded programs, ask questions, share opportunities, save listings, and request CV/SOP reviews and appointments by email.

Built with **Python 3 + Django 5.1 + PostgreSQL (SQLite locally) + Tailwind CSS + Alpine.js**. Designed to run on free tiers; the only thing you pay for is your domain.

- Architecture, database schema, roles and page map: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Free deployment guide and checklist: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- The homepage mockup this design follows: [`docs/reference/homepage-mockup.png`](docs/reference/homepage-mockup.png)

---

## 1. Run it on your computer (VS Code)

You need **Python 3.11 or newer** ([python.org/downloads](https://www.python.org/downloads/)). On Windows, tick **"Add Python to PATH"** during installation. Node.js is **not** needed.

1. Unzip the folder and open it in VS Code: **File → Open Folder… → `appfeewaiver`**.
2. Open the terminal: **Terminal → New Terminal**.
3. Run these commands **one at a time, in this order**.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py load_demo_data
python manage.py runserver
```

> If PowerShell says "running scripts is disabled", run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try step 2 again.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py load_demo_data
python manage.py runserver
```

4. Open **http://127.0.0.1:8000** in your browser.

| What | Where |
|---|---|
| Website | http://127.0.0.1:8000 |
| Django Admin | http://127.0.0.1:8000/admin/ (log in with the superuser you created) |
| Dashboard (stats) | http://127.0.0.1:8000/dashboard/ |
| Moderation queue | http://127.0.0.1:8000/moderation/ |
| Demo member login | `amina.demo@example.com` / `demo-password-123` |

`createsuperuser` asks for an **email**, a **full name** and a **password**. That account is the Administrator.

**Next time** you only need to activate the environment and start the server:

```powershell
.venv\Scripts\Activate.ps1      # Windows   (macOS/Linux: source .venv/bin/activate)
python manage.py runserver
```

VS Code also has a ready-made **Run and Debug → "Run App Fee Waiver (Django)"** launcher (select the `.venv` interpreter when VS Code asks).

### Emails while developing
Verification and password-reset emails are **printed in the terminal** where `runserver` runs. Copy the link from there.

---

## 2. First things to set in Django Admin

Open **Admin → Site configuration → Site settings**:

- **Primary email**: set the App Fee Waiver address. Every "Submit CV", "Submit SOP", "Request Appointment" and contact button uses these addresses, so changing them here updates the whole site. Leave the specific addresses blank to use the primary one everywhere.
- **Member count display**: shown on the site (default **2,000+**).
- **Community group name / URL** (optional): adds a "Join Our Group" card (for example your WhatsApp or Telegram group).
- **Announcement banner** (optional): a one-line message at the top of every page.

## 3. Roles

| Role | How to assign | Can do |
|---|---|---|
| Member | Anyone who signs up | Post, comment, like, save, submit opportunities, edit/delete own content, report |
| Moderator | Admin → Users → select → action **"Make selected members Moderators"**, or `python manage.py create_moderator email@example.com` | Everything a member can, plus: moderation queue, verify/reject opportunities, remove/restore posts and comments, warn/suspend authors, dashboard, limited Django Admin |
| Administrator | `python manage.py createsuperuser` | Everything |

## 4. Demo data

`python manage.py load_demo_data` adds clearly-labelled demo members ("(Demo)" in their names), posts, fictional opportunities (example.edu links) and starter guides.

Remove **all** of it before launch:

```bash
python manage.py remove_demo_data
```

> The demo guides are authored by the demo team account, so they are removed too. To keep one, change its **Author** in Admin → Resources first.

## 5. Tests

```bash
python manage.py test
```

29 automated tests cover sign-up/login, email verification, posting, comments and notifications, likes/saves, search, filters, opportunity verification, moderation, Site Settings emails and page rendering.

## 6. Changing the design (Tailwind CSS)

The project ships a ready-built `static/css/tailwind.css`, so the site looks right without Node.js. If you add **new** Tailwind classes to templates, do one of these:

- **Quick (no install):** set `TAILWIND_USE_CDN=True` in `.env` while you work. The page loads Tailwind from its CDN and picks up any class.
- **Rebuild the file (before deploying):** install [Node.js](https://nodejs.org/), then
  ```bash
  npm install
  npm run build:css
  ```
  Commit the updated `static/css/tailwind.css`.

Shared component styles (buttons, cards, badges, forms) live in `static/css/components.css`. Brand colours are in `tailwind.config.js` (`navy` and `brand`).

## 7. Project structure

```
appfeewaiver/          Django settings, root URLs, WSGI
core/                  Home, About, Contact, policies, global search, dashboard, Site Settings, demo-data commands
accounts/              Custom email-login User, Profile, sign-up/login/password, profile pages, saved items
community/             Posts, categories, comments + replies, likes, saved posts, success stories
opportunities/         Opportunities, types, filters, submissions, verification, saved opportunities
resources/             Resource library and categories
support/               Expert Support, CV & SOP Review, appointment requests (mailto: only)
notifications/         On-site notifications and admin announcements
moderation/            Reports, moderation queue, warnings/suspensions
templates/             All HTML templates (base layout, partials, pages)
static/                CSS, JS, logo and images
docs/                  Architecture, deployment guide, design reference
```

## 8. Put it on GitHub

1. Create an empty repository on github.com (no README), e.g. `appfeewaiver`.
2. In the VS Code terminal:
   ```bash
   git init
   git add .
   git commit -m "App Fee Waiver version 1"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/appfeewaiver.git
   git push -u origin main
   ```
3. Check on GitHub that **`.env` and `db.sqlite3` are NOT listed**. `.gitignore` excludes them, along with any PDF files, so CVs and SOPs can't be committed by accident.

Then follow [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) to go live.

## 9. Important Version 1 decisions

- **CVs and SOPs are never uploaded or stored.** Members email them using pre-filled `mailto:` links.
- **Appointments are requested by email.** No Calendly or paid scheduling.
- **No paid services.** Everything runs on free/open-source software and free tiers.
- **No invented statistics.** The homepage shows the configured member count (2,000+) and only numbers calculated from the database.
