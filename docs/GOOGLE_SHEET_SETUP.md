# Funding Testimonies: Google Form → Google Sheet → Website

Everything here is free. There are no Google API keys or service accounts. A small script inside
your Google Sheet publishes **only approved rows**, and it is protected by a secret token.

```
Member fills in Google Form ─▶ Google Sheet (new row)
                                   │  you type YES in the "Approved" column
                                   ▼
             Apps Script web app (returns approved rows only, needs the token)
                                   │  the website checks it automatically (every 60 min by default)
                                   ▼
                    Django saves/updates the testimony ─▶ shown on the website
```

## 1. Create the Google Form

Create a form (forms.google.com) with these questions. The wording can change a little:
the website matches columns by keywords (shown in brackets).

| Question | Type | Required | Matched by |
|---|---|---|---|
| Full Name | Short answer | Yes | "full name" / "name" |
| Email Address | Short answer | Yes | "email" (private, never shown on the website) |
| Degree / Program | Short answer | Yes | "degree", "program", "course" |
| University | Short answer | Yes | "university", "institution", "school" |
| Country | Short answer | Yes | "country" |
| What did you receive? | Multiple choice: Fully Funded, Scholarship, Admission, Application Fee Waiver, Assistantship, Fellowship, Other | Yes | "receive", "type", "category", "success" |
| Your testimony | Paragraph | Yes | "testimony", "story", "experience" |
| Photo link (optional) | Short answer | No | "photo", "picture", "image" |
| Do you give permission to publish your testimony on the website? | Multiple choice: "Yes, I agree" / "No" | Yes | "permission", "consent" |

Tips:
- Don't use Google Forms' **file upload** question for photos: it forces people to sign in and the
  files stay private. A "Photo link" question is simpler. If nobody adds a photo, the card shows the
  person's initials.
- Only rows answered **"Yes…"** to the permission question are ever imported.

In the form, open **Responses → Link to Sheets** to create the response sheet.

## 2. Add the "Approved" column

In the response sheet, add a column header **`Approved`** right after the last question column.
To publish a testimony, type **YES** in that row. Leave it empty (or type NO) to keep it off the website.

> Tip: select the Approved column → Data → Data validation → Dropdown with `YES` and `NO`.

## 3. Add the script

1. In the sheet: **Extensions → Apps Script**.
2. Delete everything in `Code.gs` and paste the contents of [`google-apps-script.js`](google-apps-script.js).
3. If your response tab isn't called `Form Responses 1`, change `SHEET_NAME` at the top.
4. Click **Save**.

## 4. Set the secret token

1. Make a long random token, e.g. on your computer:
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Apps Script → **Project Settings** (gear icon) → **Script properties** → **Add script property**:
   - Property: `SYNC_TOKEN`
   - Value: *your token*
3. Put the **same token** on Render: Environment → add `TESTIMONY_SYNC_TOKEN` = *your token*.

## 5. Deploy it as a web app

1. Apps Script → **Deploy → New deployment** → type **Web app**.
2. Execute as: **Me**. Who has access: **Anyone**. (Nobody can read anything without the token.)
3. Click **Deploy** and authorise when Google asks.
4. Copy the **Web app URL** (ends in `/exec`).

Check it in your browser: `<web app URL>?token=<your token>` should show `{"rows":[...]}`.

## 6. Connect the website

In **Django Admin → Site settings → Funding testimonies**:
- **Google testimony form URL**: the form's share link (the "Share Your Story" button opens it).
- **Google Apps Script sync URL**: the web app URL from step 5.
- **Testimony sync interval minutes**: default 60.

Then open **Admin → Testimonies** and click **"Sync from Google Sheet now"** to test.
Every run is listed under **Admin → Sync logs**, with how many rows were imported or skipped, or the error.

## How syncing behaves

- **Automatic:** when someone visits the site and the interval has passed, a sync runs in the
  background (visitors never wait). No paid scheduler needed.
- **Manual:** the admin button, or `python manage.py sync_testimonies`.
- **Optional external schedule:** free services like cron-job.org can call
  `https://your-site/testimonies/sync/?token=<your token>` every hour. That also keeps syncs going
  when nobody visits.
- **Never deletes:** removing YES in the sheet does **not** remove a testimony from the website.
  To take one down, untick **Published** in Admin.
- **Your edits are kept:** if you fix a typo in Admin, that testimony is marked
  "Keep admin edits" and the sheet will no longer overwrite it.
- **No duplicates:** each row has a stable ID, so re-syncing updates the row rather than adding a new one.
  (If you edit the *Timestamp* or *Email* cell of a row, it will be treated as a new testimony.)

After changing the script later, use **Deploy → Manage deployments → Edit → Version: New version**
so the URL stays the same.
