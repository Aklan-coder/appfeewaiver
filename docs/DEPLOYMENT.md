# Deploying App Fee Waiver for free

Setup: **GitHub** (code) → **Render** free web service (Django) + **Neon** free PostgreSQL
+ **Brevo** free email API + a **Google Sheet** for testimonies. The only cost is your domain.

> Free tiers change. Check current limits: [Render free](https://render.com/docs/free),
> [Neon pricing](https://neon.com/pricing), [Brevo pricing](https://www.brevo.com/pricing/).

---

## Updating the existing live site (you already have Render + Neon)

1. Replace your project folder with the new version (see the README, "Updating from the old version").
2. On your computer: `python manage.py migrate` and `python manage.py test`.
3. `git add -A`, `git commit -m "Rebuild as single-page site"`, `git push`.
4. Render → Environment → **add** the new variables below (`EMAIL_PROVIDER`, `BREVO_API_KEY`,
   `DEFAULT_FROM_EMAIL`, `TESTIMONY_SYNC_TOKEN`) and **delete** `PROFILE_PHOTO_UPLOADS_ENABLED`
   and `REQUIRE_EMAIL_VERIFICATION` if you have them.
5. Render redeploys and runs the migrations. Your admin login still works.
6. Admin → **WhatsApp groups** → add your two groups. Admin → **Site settings** → fill in.

### What happens to the old data?
The migration **does not delete** the old forum tables (posts, comments, opportunities, resources,
notifications, reports, member profiles). They just sit unused in Neon. Your admin users and the site
settings are kept (the old contact email is carried over).

When you're sure you don't need that data, you can list and then remove the old tables:

```bash
python manage.py drop_legacy_tables            # only LISTS them
python manage.py drop_legacy_tables --confirm  # actually deletes them (cannot be undone)
```
Tip: take a Neon backup/branch first (Neon dashboard → Branches → Create branch).

---

## Fresh deployment

### Step 1: Database (Neon)
1. Sign up at neon.com, create a project (pick the region closest to your Render region).
2. Copy the **connection string**: `postgresql://user:password@ep-xxxx.aws.neon.tech/neondb?sslmode=require`

### Step 2: Web service (Render)
1. render.com → **New → Web Service** → pick the `appfeewaiver` repository.
2. **Runtime:** Python 3 · **Build command:** `./build.sh` · **Start command:** `gunicorn appfeewaiver.wsgi:application` · **Instance type:** Free
3. **Environment variables:**

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `DEBUG` | `False` |
| `SECRET_KEY` | long random string: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | the Neon connection string |
| `DB_SSL_REQUIRE` | `True` |
| `ALLOWED_HOSTS` | `appfeewaiver.onrender.com,appfeewaiver.com,www.appfeewaiver.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://appfeewaiver.onrender.com,https://appfeewaiver.com,https://www.appfeewaiver.com` |
| `SITE_URL` | `https://appfeewaiver.com` (or the onrender.com URL until the domain is ready) |
| `EMAIL_PROVIDER` | `brevo` |
| `BREVO_API_KEY` | from Brevo ([EMAIL_SETUP.md](EMAIL_SETUP.md)) |
| `DEFAULT_FROM_EMAIL` | `App Fee Waiver <appfeewaiver@gmail.com>` (a Brevo-verified sender) |
| `TESTIMONY_SYNC_TOKEN` | long random string, same as in the Apps Script ([GOOGLE_SHEET_SETUP.md](GOOGLE_SHEET_SETUP.md)) |

4. **Create Web Service.** `build.sh` installs packages, collects static files and runs migrations.

### Step 3: Admin account
Render → service → **Shell**: `python manage.py createsuperuser`.
If Shell isn't available on the free plan, run it on your computer with `DATABASE_URL` in your local
`.env` temporarily set to the Neon string, then set it back. There is no public admin sign-up.

### Step 4: Set up in Admin (`/admin/`)
1. **WhatsApp groups → Add**: "Community Group 1" + invite link; then "Community Group 2" + invite link.
   New registrations alternate between active groups. Set a **capacity** to stop assigning a group once full.
2. **Site settings**: member count (e.g. `2,000+`), contact email, the testimony form + sync URLs,
   the answer to "Is the community free?" (hidden until you write it), and social links (icons appear only when set).
3. Register yourself on the live site to check the welcome email arrives.

### Step 5: Domain
Render → **Settings → Custom Domains** → add `appfeewaiver.com` and `www.appfeewaiver.com`, add the DNS
records Render shows at your registrar. HTTPS is automatic. Update `SITE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.

---

## Checklist
- [ ] `DEBUG=False`, new random `SECRET_KEY` (never committed)
- [ ] `DATABASE_URL` → Neon, `DB_SSL_REQUIRE=True`
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` include the real domain
- [ ] `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`, verified `DEFAULT_FROM_EMAIL`, and a test registration received the email
- [ ] Two WhatsApp groups added and active
- [ ] `TESTIMONY_SYNC_TOKEN` set in Render and in the Apps Script; "Sync from Google Sheet now" succeeds
- [ ] No demo data in production (`python manage.py remove_demo_data`)
- [ ] Phone test: register, open menu, FAQ, testimonies filters

## Security (already configured)
- The WhatsApp links live only in the database and in the welcome email. They are never in page HTML or JavaScript.
- The success message is identical for new and already-registered emails (nobody can check who registered).
- Rate limit (6 registration attempts per hour per IP) and a hidden honeypot field against bots.
- Testimony emails are private: never shown on the website.
- Only approved rows with publishing permission are imported; syncs never delete anything.
- With `DEBUG=False`: HTTPS redirect, secure cookies, HSTS, clickjacking and no-sniff headers.
- Secrets only in environment variables; `.env` is git-ignored.
- If you ever run more than one Gunicorn worker, set `CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache`,
  `CACHE_LOCATION=cache_table` and run `python manage.py createcachetable` so rate limits are shared.

## Keeping testimonies syncing
The site checks the sheet on its own when people visit (every 60 minutes by default). Render's free service
sleeps after ~15 minutes without visitors, so a sync may wait until the next visit. For a fixed schedule, a free
service such as cron-job.org can open `https://appfeewaiver.com/testimonies/sync/?token=YOUR_TOKEN` hourly
(this also wakes the site up).

## Updating later
Push to `main` on GitHub. Render redeploys and runs migrations automatically.
