# Deploying App Fee Waiver for free

Target setup: **GitHub** (code) → **Render** free web service (Django) + **Neon** free PostgreSQL + your domain.

> Free tiers change. Check the current limits before you start: [Render free tier](https://render.com/docs/free), [Neon free plan](https://neon.com/pricing).

---

## Before you deploy

1. Remove demo content locally if you loaded it: `python manage.py remove_demo_data`.
2. Run the tests: `python manage.py test` (all should pass).
3. If you changed templates with new Tailwind classes, rebuild the CSS (`npm run build:css`) and commit it.
4. Push to GitHub (see README section 8). Confirm `.env` is **not** in the repository.

## Step 1: Create the database (Neon)

1. Sign up at [neon.com](https://neon.com) (free, no card needed at the time of writing).
2. Create a project (choose the region closest to your Render region).
3. Copy the **connection string**. It looks like
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`

## Step 2: Create the web service (Render)

1. Sign up at [render.com](https://render.com) with your GitHub account.
2. **New → Web Service** → pick your `appfeewaiver` repository.
3. Settings:
   - **Runtime:** Python 3
   - **Build command:** `./build.sh`
   - **Start command:** `gunicorn appfeewaiver.wsgi:application`
   - **Instance type:** Free
4. **Environment variables** (Environment tab):

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `DEBUG` | `False` |
| `SECRET_KEY` | a long random string: run `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | the Neon connection string |
| `DB_SSL_REQUIRE` | `True` |
| `ALLOWED_HOSTS` | `your-app.onrender.com,appfeewaiver.com,www.appfeewaiver.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com,https://appfeewaiver.com,https://www.appfeewaiver.com` |
| `SITE_URL` | `https://appfeewaiver.com` (or the onrender.com URL until your domain is ready) |
| `PROFILE_PHOTO_UPLOADS_ENABLED` | `False` (Render's free disk is wiped on every deploy; members get initials avatars) |

(Alternatively, use **New → Blueprint** and Render reads `render.yaml`; you still paste the values marked `sync: false`.)

5. Click **Create Web Service**. `build.sh` installs packages, collects static files and runs migrations. Categories, opportunity types and the Moderator role are created automatically.

## Step 3: Create your admin account

In Render, open your service → **Shell** and run:

```bash
python manage.py createsuperuser
```

If Shell isn't available on the free plan, run the same command **on your computer** with `DATABASE_URL` in your local `.env` temporarily set to the Neon string, then set it back.

Then log in at `https://your-app.onrender.com/admin/` → **Site settings** → set the emails.

## Step 4: Connect your domain

1. Render → your service → **Settings → Custom Domains → Add** `appfeewaiver.com` and `www.appfeewaiver.com`.
2. At your domain registrar, add the DNS records Render shows you (usually a CNAME for `www` and an A/ALIAS record for the root).
3. Render issues a free HTTPS certificate automatically.
4. Update `SITE_URL`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` if you haven't already.

## Step 5 (optional): Outgoing email

Needed for email verification and "forgot password". With Gmail (free):

1. Turn on 2-Step Verification for the Google account, then create an **App Password**.
2. Add in Render:

| Key | Value |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | the Gmail address |
| `EMAIL_HOST_PASSWORD` | the App Password |
| `DEFAULT_FROM_EMAIL` | `App Fee Waiver <that address>` |

3. Once emails arrive reliably, you may set `REQUIRE_EMAIL_VERIFICATION=True` so only confirmed members can post.

---

## Deployment checklist

- [ ] Demo data removed (`remove_demo_data`)
- [ ] Tests pass locally
- [ ] `DEBUG=False` in production
- [ ] New random `SECRET_KEY` set in Render (never committed)
- [ ] `DATABASE_URL` points to Neon, `DB_SSL_REQUIRE=True`
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` include your real domain with `https://`
- [ ] `PROFILE_PHOTO_UPLOADS_ENABLED=False` on hosts without a permanent disk
- [ ] Superuser created; Site Settings emails configured
- [ ] At least one moderator assigned
- [ ] Privacy Policy and Terms reviewed by your team
- [ ] Visit `/sitemap.xml` and `/robots.txt` on the live domain
- [ ] Test on a phone: sign up, post, comment, save, CV/SOP email buttons

## Security notes (already configured)

- CSRF protection on every form; passwords hashed by Django (PBKDF2).
- With `DEBUG=False`: HTTPS redirect, secure cookies, HSTS, `X-Frame-Options: DENY`, no-sniff, strict referrer policy.
- Rate limits on sign-up, login, password reset, posting, commenting, reporting and submissions; honeypot fields on public forms.
- Secrets only in environment variables; `.env` is git-ignored.
- Members' emails are never shown publicly.
- If you run more than one Gunicorn worker, set `CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache`, `CACHE_LOCATION=cache_table` and run `python manage.py createcachetable` so rate limits are shared.

## Updating the live site

Push to the `main` branch on GitHub; Render redeploys automatically and runs migrations. After changing models locally, run `python manage.py makemigrations`, commit the new migration files, then push.
