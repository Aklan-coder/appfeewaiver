# Welcome emails (the WhatsApp link) with Brevo, free

Render's free web services block outgoing SMTP (ports 25/465/587), so Gmail SMTP won't work there.
The site therefore sends email through **Brevo's HTTPS API**, which works on Render's free plan.
Brevo's free plan allows **300 emails/day**, with a small "Sent with Brevo" footer.

## 1. Create the Brevo account
1. Sign up at brevo.com (free plan).
2. **Senders, Domains & Dedicated IPs → Senders → Add a sender.** Use the address people should see,
   e.g. `appfeewaiver@gmail.com`, and click the confirmation link Brevo emails you.
   - Once you own your domain, add it under **Domains** and authenticate it (DKIM/DMARC records).
     Emails from your own domain are less likely to land in spam.

## 2. Create an API key
**Settings (top-right) → SMTP & API → API keys → Generate a new API key.** Copy it (it starts with `xkeysib-`).
Treat it like a password: it goes in Render only, never in GitHub.

## 3. Add the settings on Render
Render → your service → **Environment**:

| Key | Value |
|---|---|
| `EMAIL_PROVIDER` | `brevo` |
| `BREVO_API_KEY` | your key |
| `DEFAULT_FROM_EMAIL` | `App Fee Waiver <appfeewaiver@gmail.com>` (must be the verified sender) |

Save. Render redeploys automatically.

## 4. Test
Register on the live site with your own email. Then in **Admin → Registrations**:
- **Link sent ✔** means it worked.
- **✘** means it failed: open that registration and the **Email error** field tells you why (e.g. `Brevo HTTP 401` means a wrong API key;
  `sender not valid` means the sender isn't verified).
  Fix it, select the registrations and run **"Resend WhatsApp email"**.

The dashboard's **Email Delivery Failures** card counts registrations whose email hasn't gone out.

## Locally
With `EMAIL_PROVIDER=console` (the default in `.env.example`), emails are printed in the VS Code
terminal instead of being sent.

## Other providers
`EMAIL_PROVIDER=smtp` with `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
works on hosts that allow SMTP (not Render's free plan).
