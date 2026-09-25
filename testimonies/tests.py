from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import SiteSettings

from . import sync
from .models import SuccessType, SyncLog, Testimony


class CacheClearedTestCase(TestCase):
    """Site settings and rate limits live in the cache; start every test clean."""

    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()


def sheet_row(**overrides):
    row = {
        "_id": "row-1",
        "Timestamp": "2026-09-01T10:00:00Z",
        "Full Name": "Chioma N.",
        "Email Address": "chioma@private.example",
        "Degree / Program": "MSc Data Science",
        "University": "University of Toronto",
        "Country": "Canada",
        "What did you receive?": "Fully funded admission",
        "Your testimony": "The community helped me find a fee waiver and a full scholarship.",
        "Photo (optional)": "",
        "Do you give permission to publish your testimony on the website?": "Yes, I agree",
        "Approved": "YES",
    }
    row.update(overrides)
    return row


class SyncImportTests(CacheClearedTestCase):
    def test_imports_only_approved_rows_with_consent(self):
        rows = [
            sheet_row(),
            sheet_row(_id="row-2", Approved=""),
            sheet_row(_id="row-3", Approved="NO"),
            sheet_row(**{"_id": "row-4", "Do you give permission to publish your testimony on the website?": "No"}),
        ]
        created, updated, skipped = sync.import_rows(rows)
        self.assertEqual((created, updated, skipped), (1, 0, 3))
        t = Testimony.objects.get()
        self.assertEqual(t.external_id, "row-1")
        self.assertEqual(t.success_type, SuccessType.FULLY_FUNDED)
        self.assertEqual(t.university, "University of Toronto")
        self.assertTrue(t.published)

    def test_column_order_does_not_matter(self):
        row = sheet_row()
        consent_key = "Do you give permission to publish your testimony on the website?"
        reordered = {consent_key: row.pop(consent_key), **dict(reversed(list(row.items())))}
        sync.import_rows([reordered])
        t = Testimony.objects.get()
        self.assertEqual(t.name, "Chioma N.")
        self.assertTrue(t.testimony.startswith("The community helped"))
        self.assertEqual(t.email, "chioma@private.example")

    def test_no_duplicates_and_updates_existing(self):
        sync.import_rows([sheet_row()])
        sync.import_rows([sheet_row()])
        self.assertEqual(Testimony.objects.count(), 1)
        created, updated, _ = sync.import_rows([sheet_row(**{"Your testimony": "Updated story."})])
        self.assertEqual((created, updated), (0, 1))
        self.assertEqual(Testimony.objects.get().testimony, "Updated story.")

    def test_rows_without_id_are_deduplicated_by_hash(self):
        row = sheet_row()
        del row["_id"]
        sync.import_rows([row])
        sync.import_rows([row])
        self.assertEqual(Testimony.objects.count(), 1)

    def test_admin_edits_are_kept(self):
        sync.import_rows([sheet_row()])
        Testimony.objects.update(testimony="Edited by admin", keep_admin_edits=True)
        sync.import_rows([sheet_row(**{"Your testimony": "Sheet text"})])
        self.assertEqual(Testimony.objects.get().testimony, "Edited by admin")

    def test_unpublished_by_admin_stays_unpublished(self):
        sync.import_rows([sheet_row()])
        Testimony.objects.update(published=False)
        sync.import_rows([sheet_row(**{"Your testimony": "Changed"})])
        self.assertFalse(Testimony.objects.get().published)

    def test_sync_never_deletes(self):
        sync.import_rows([sheet_row(), sheet_row(_id="row-2")])
        sync.import_rows([])
        sync.import_rows([sheet_row(_id="row-2", Approved="NO")])
        self.assertEqual(Testimony.objects.count(), 2)

    def test_success_type_mapping_and_drive_photo(self):
        self.assertEqual(sync.map_success_type("Application fee waiver"), SuccessType.FEE_WAIVER)
        self.assertEqual(sync.map_success_type("Scholarship"), SuccessType.SCHOLARSHIP)
        self.assertEqual(sync.map_success_type("Graduate assistantship"), SuccessType.ASSISTANTSHIP)
        self.assertEqual(sync.map_success_type("Something else"), SuccessType.OTHER)
        self.assertEqual(
            sync.public_photo_url("https://drive.google.com/open?id=1AbCdEfGhIjKlMn"),
            "https://drive.google.com/thumbnail?id=1AbCdEfGhIjKlMn&sz=w240",
        )
        self.assertEqual(sync.public_photo_url("javascript:alert(1)"), "")

    @override_settings(TESTIMONY_SYNC_TOKEN="tok")
    def test_run_sync_logs_success_and_failure(self):
        site = SiteSettings.load()
        site.testimony_sync_url = "https://script.google.com/macros/s/x/exec"
        site.save()
        with mock.patch.object(sync, "fetch_rows", return_value=[sheet_row()]):
            log = sync.run_sync()
        self.assertEqual(log.status, SyncLog.Status.SUCCESS)
        self.assertEqual(log.created, 1)
        with mock.patch.object(sync, "fetch_rows", side_effect=sync.SyncError("boom")):
            log = sync.run_sync()
        self.assertEqual(log.status, SyncLog.Status.FAILED)
        self.assertEqual(Testimony.objects.count(), 1)

    def test_run_sync_without_config_fails_cleanly(self):
        log = sync.run_sync()
        self.assertEqual(log.status, SyncLog.Status.FAILED)
        self.assertIn("not set", log.message)


class TestimonyPageTests(CacheClearedTestCase):
    def setUp(self):
        self.public = Testimony.objects.create(
            name="Visible Person", email="secret@private.example", testimony="Public story",
            success_type=SuccessType.SCHOLARSHIP,
        )
        self.hidden = Testimony.objects.create(name="Hidden Person", testimony="Hidden story", published=False)

    def test_unpublished_hidden_and_email_never_shown(self):
        for path in ["/", reverse("testimonies:list")]:
            html = self.client.get(path).content.decode()
            self.assertIn("Visible Person", html)
            self.assertNotIn("Hidden Person", html)
            self.assertNotIn("secret@private.example", html)

    def test_home_testimonies_move_when_there_are_enough(self):
        self.assertNotContains(self.client.get("/"), "data-marquee")  # only 1 published: static
        for i in range(3):
            Testimony.objects.create(name=f"Person {i}", testimony="Story")
        html = self.client.get("/").content.decode()
        self.assertIn("data-marquee", html)
        self.assertNotIn("Hidden Person", html)

    def test_category_filter(self):
        Testimony.objects.create(name="Admit Person", testimony="x", success_type=SuccessType.ADMISSION)
        html = self.client.get(reverse("testimonies:list"), {"type": "admission"}).content.decode()
        self.assertIn("Admit Person", html)
        self.assertNotIn("Visible Person", html)
        self.assertEqual(self.client.get(reverse("testimonies:list"), {"type": "bogus"}).status_code, 200)

    def test_empty_state(self):
        Testimony.objects.all().delete()
        self.assertContains(self.client.get(reverse("testimonies:list")), "Share")


class SyncEndpointTests(CacheClearedTestCase):
    url = "/testimonies/sync/"

    @override_settings(TESTIMONY_SYNC_TOKEN="")
    def test_disabled_without_token_setting(self):
        self.assertEqual(self.client.get(self.url, {"token": ""}).status_code, 403)

    @override_settings(TESTIMONY_SYNC_TOKEN="right-token")
    def test_requires_correct_token(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(self.url, {"token": "wrong"}).status_code, 403)
        with mock.patch("testimonies.views.run_sync") as run:
            run.return_value = SyncLog(status="success", message="ok")
            response = self.client.get(self.url, {"token": "right-token"})
        self.assertEqual(response.status_code, 200)
        run.assert_called_once()


class TestimonyAdminTests(CacheClearedTestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(email="boss@example.com", password="pw-12345-xyz")
        self.client.force_login(user)
        self.t = Testimony.objects.create(name="A", testimony="Story", published=False)
        self.changelist = reverse("admin:testimonies_testimony_changelist")

    def test_publish_action(self):
        self.client.post(self.changelist, {"action": "publish", "_selected_action": [self.t.pk]})
        self.t.refresh_from_db()
        self.assertTrue(self.t.published)

    def test_editing_content_sets_keep_admin_edits(self):
        Testimony.objects.filter(pk=self.t.pk).update(external_id="sheet-row-9")
        url = reverse("admin:testimonies_testimony_change", args=[self.t.pk])
        form = self.client.get(url).context["adminform"].form
        data = {k: v for k, v in form.initial.items() if v is not None}
        data.update(testimony="Fixed a typo", success_type="other", published="on")
        data = {k: ("on" if v is True else v) for k, v in data.items() if v is not False}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        self.t.refresh_from_db()
        self.assertEqual(self.t.testimony, "Fixed a typo")
        self.assertTrue(self.t.keep_admin_edits)

    @override_settings(TESTIMONY_SYNC_TOKEN="tok")
    def test_sync_now_button(self):
        with mock.patch("testimonies.admin.run_sync") as run:
            run.return_value = SyncLog(status="success", message="ok")
            response = self.client.post(reverse("admin:testimonies_sync_now"))
        self.assertEqual(response.status_code, 302)
        run.assert_called_once()
