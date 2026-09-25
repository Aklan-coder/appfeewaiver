"""
Import approved testimonies from the Google Sheet behind the Google Form.

How it works (free, no Google API keys in Django):
  Google Form -> Google Sheet -> a small Google Apps Script "web app" attached to
  the sheet (docs/google-apps-script.js) returns ONLY rows where Approved = YES,
  protected by a shared secret token -> this module saves them as Testimony rows.

Safe by design:
  * only approved rows with permission to publish are imported;
  * each row has a stable ID, so re-running never creates duplicates;
  * nothing on the website is ever deleted by a sync;
  * testimonies you edited in Admin are not overwritten;
  * every run is recorded in SyncLog.
"""
import hashlib
import json
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import SiteSettings

from .models import SuccessType, SyncLog, Testimony

logger = logging.getLogger(__name__)

YES_VALUES = {"yes", "y", "true", "approved", "1", "✓", "✔"}
CONSENT_WORDS = ("yes", "i agree", "agree", "i consent", "consent", "true", "allow")


class SyncError(Exception):
    pass


# ---------------------------------------------------------------------------
# Reading the sheet
# ---------------------------------------------------------------------------
def fetch_rows(url, token, timeout=20):
    if not url:
        raise SyncError("The Google Apps Script sync URL is not set (Admin → Site settings).")
    if not token:
        raise SyncError("TESTIMONY_SYNC_TOKEN environment variable is not set.")
    separator = "&" if "?" in url else "?"
    full_url = f"{url}{separator}{urllib.parse.urlencode({'token': token})}"
    try:
        with urllib.request.urlopen(full_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise SyncError(f"Could not read the Google Sheet: {exc}") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise SyncError(f"Google Apps Script said: {payload['error']}")
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SyncError("Unexpected response from the Google Apps Script.")
    return rows


# ---------------------------------------------------------------------------
# Mapping sheet columns (matched by keywords, so form questions can be reworded)
# ---------------------------------------------------------------------------
def _norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _pick(row, *keywords, exclude=()):
    for key, value in row.items():
        k = _norm(key)
        if any(word in k for word in keywords) and not any(bad in k for bad in exclude):
            return str(value or "").strip()
    return ""


def _is_yes(value):
    return _norm(value) in YES_VALUES


def _has_consent(value):
    v = _norm(value)
    return any(v.startswith(word) for word in CONSENT_WORDS)


def map_success_type(value):
    v = _norm(value)
    if "fully" in v:
        return SuccessType.FULLY_FUNDED
    if "waiver" in v or "fee" in v:
        return SuccessType.FEE_WAIVER
    if "scholar" in v:
        return SuccessType.SCHOLARSHIP
    if "admission" in v or "admit" in v:
        return SuccessType.ADMISSION
    if "assistant" in v:
        return SuccessType.ASSISTANTSHIP
    if "fellow" in v:
        return SuccessType.FELLOWSHIP
    return SuccessType.OTHER


def public_photo_url(value):
    """Accept http(s) links; turn Google Drive links into a thumbnail link."""
    value = (value or "").strip().split(",")[0].strip()
    if not value.startswith(("http://", "https://")):
        return ""
    match = re.search(r"drive\.google\.com/.*(?:id=|/d/)([\w-]{10,})", value)
    if match:
        return f"https://drive.google.com/thumbnail?id={match.group(1)}&sz=w240"
    return value[:500]


def parse_row(row):
    """Return a dict of Testimony fields, or None if the row must not be published."""
    approved = _pick(row, "approved", "approve")
    if not _is_yes(approved):
        return None
    consent = _pick(row, "permission", "consent", "agree", "publish", exclude=("approved",))
    if consent and not _has_consent(consent):
        return None
    name = _pick(row, "full name", exclude=("university", "school", "program", "institution")) or _pick(
        row, "name", exclude=("university", "school", "program", "institution", "email")
    )
    testimony = _pick(row, "testimony", "story", "experience", exclude=("permission", "consent", "publish", "agree", "approved"))
    if not name or not testimony:
        return None
    email = _pick(row, "email")
    timestamp = _pick(row, "timestamp", "submitted")
    external_id = str(row.get("_id") or "").strip() or hashlib.sha256(
        f"{timestamp}|{email}|{name}".encode()
    ).hexdigest()[:40]
    submitted_at = parse_datetime(timestamp) if timestamp else None
    if submitted_at and timezone.is_naive(submitted_at):
        submitted_at = timezone.make_aware(submitted_at)
    return {
        "external_id": external_id[:64],
        "name": name[:120],
        "email": email[:254] if "@" in email else "",
        "program": _pick(row, "degree", "program", "course")[:150],
        "university": _pick(row, "university", "institution", "school")[:150],
        "country": _pick(row, "country")[:80],
        "success_type": map_success_type(
            _pick(row, "success", "type", "category", "receive", exclude=("permission", "consent", "publish", "approved"))
        ),
        "testimony": testimony[:2000],
        "photo_url": public_photo_url(_pick(row, "photo", "picture", "image")),
        "submitted_at": submitted_at,
    }


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------
def import_rows(rows):
    created = updated = skipped = 0
    now = timezone.now()
    for row in rows:
        if not isinstance(row, dict):
            skipped += 1
            continue
        data = parse_row(row)
        if data is None:
            skipped += 1
            continue
        existing = Testimony.objects.filter(external_id=data["external_id"]).first()
        if existing is None:
            Testimony.objects.create(**data, imported_at=now, published=True)
            created += 1
        elif existing.keep_admin_edits:
            skipped += 1
        else:
            changed = False
            for field, value in data.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                existing.imported_at = now
                existing.save()  # published/featured flags are never touched by the sync
                updated += 1
    return created, updated, skipped


def run_sync(trigger="manual"):
    """Fetch and import. Always returns a SyncLog (never raises)."""
    site = SiteSettings.load()
    log = SyncLog.objects.create(status=SyncLog.Status.FAILED, trigger=trigger)
    try:
        rows = fetch_rows(site.testimony_sync_url, settings.TESTIMONY_SYNC_TOKEN)
        created, updated, skipped = import_rows(rows)
        log.status = SyncLog.Status.SUCCESS
        log.rows_received, log.created, log.updated, log.skipped = len(rows), created, updated, skipped
        log.message = f"{created} new, {updated} updated, {skipped} skipped (not approved, no permission or unchanged edits)."
    except SyncError as exc:
        log.message = str(exc)
    except Exception as exc:  # never let a sync crash a page
        logger.exception("Testimony sync failed")
        log.message = f"Unexpected error: {exc}"
    log.finished_at = timezone.now()
    log.save()
    return log


def maybe_auto_sync():
    """
    Called when someone views testimonies. If the configured interval has passed,
    sync in a background thread so the visitor never waits. Free: no scheduler needed.
    """
    site = SiteSettings.load()
    if not site.testimony_sync_url or not settings.TESTIMONY_SYNC_TOKEN:
        return
    interval = timedelta(minutes=max(site.testimony_sync_interval_minutes, 5))
    last = SyncLog.objects.exclude(trigger="manual").only("started_at").first()
    if last and timezone.now() - last.started_at < interval:
        return
    if not cache.add("testimony-sync-lock", 1, 300):
        return  # another sync is already running

    def _worker():
        try:
            run_sync(trigger="auto")
        finally:
            cache.delete("testimony-sync-lock")
            close_old_connections()

    threading.Thread(target=_worker, daemon=True).start()
