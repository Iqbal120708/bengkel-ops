from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer, Vehicle
from automation.models import FollowUp
from automation.views import _pending_meta_oob

User = get_user_model()


class FollowUpTestBase(TestCase):
    """Setup data bersama: user tiap role, customer, vehicle, followup."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="test1234", role="OWNER"
        )
        self.admin = User.objects.create_user(
            username="admin", password="test1234", role="ADMIN"
        )
        self.customer = Customer.objects.create(
            name="Andi Saputra", phone="081546919836"
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer,
            plate_number="D 1234 ABC",
            brand="Honda",
            model_name="Vario",
            vehicle_type="MOTOR",
            status="INACTIVE",
            last_service_date=date.today() - timedelta(days=95),
        )
        self.pending_followup = FollowUp.objects.create(
            vehicle=self.vehicle,
            type="REACTIVATION",
            priority="HIGH",
            scheduled_at=date.today(),
            status="PENDING",
        )


class FollowUpAccessControlTest(FollowUpTestBase):

    def test_owner_can_access_followup_list(self):
        """Owner (superuser) harus bisa buka halaman follow-up."""
        self.client.force_login(self.owner)
        response = self.client.get(reverse("automation:followup_list"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_followup_list(self):
        """Admin/Kasir termasuk role yang diizinkan role_required."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("automation:followup_list"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_denied(self):
        """Belum login harus di-redirect/ditolak, bukan dapat 200."""
        response = self.client.get(reverse("automation:followup_list"))
        self.assertNotEqual(response.status_code, 200)

    def test_other_role_denied(self):
        """Role di luar OWNER/ADMIN harus dapat 403, bukan lolos."""
        other = User.objects.create_user(
            username="lainnya", password="test1234", role="KASIR_LAIN"
        )
        self.client.force_login(other)
        response = self.client.get(reverse("automation:followup_list"))
        self.assertEqual(response.status_code, 403)


class FollowUpCompleteTest(FollowUpTestBase):

    def test_complete_updates_status(self):
        """POST complete harus ubah status jadi COMPLETED dan isi completed_at."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("automation:followup_complete", args=[self.pending_followup.pk])
        )
        self.pending_followup.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.pending_followup.status, "COMPLETED")
        self.assertIsNotNone(self.pending_followup.completed_at)

    def test_complete_fails_if_not_pending(self):
        """FollowUp yang sudah COMPLETED tidak boleh di-complete ulang."""
        self.pending_followup.status = "COMPLETED"
        self.pending_followup.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("automation:followup_complete", args=[self.pending_followup.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_complete_via_get_rejected(self):
        """Endpoint ini cuma nerima POST, GET harus 405."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("automation:followup_complete", args=[self.pending_followup.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_complete_response_contains_oob_fragment(self):
        """Response harus bawa OOB fragment buat update counter di halaman."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("automation:followup_complete", args=[self.pending_followup.pk])
        )
        content = response.content.decode()
        self.assertIn("followup-count", content)
        self.assertIn("hx-swap-oob", content)


class FollowUpCancelTest(FollowUpTestBase):

    def test_cancel_updates_status(self):
        """POST cancel harus ubah status jadi CANCELLED."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("automation:followup_cancel", args=[self.pending_followup.pk])
        )
        self.pending_followup.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.pending_followup.status, "CANCELLED")

    def test_cancel_does_not_fill_completed_at(self):
        """Cancel beda dari complete, completed_at harus tetap kosong."""
        self.client.force_login(self.admin)
        self.client.post(
            reverse("automation:followup_cancel", args=[self.pending_followup.pk])
        )
        self.pending_followup.refresh_from_db()
        self.assertIsNone(self.pending_followup.completed_at)


class PendingMetaOobTest(FollowUpTestBase):

    def test_empty_row_not_sent_when_pending_exists(self):
        """Elemen baris kosong tidak boleh dikirim sama sekali kalau masih ada pending."""
        html = _pending_meta_oob()
        self.assertIn("1 Pending", html)
        self.assertNotIn("followup-empty-row", html)

    def test_empty_row_sent_when_no_pending_left(self):
        """Elemen baris kosong baru dikirim begitu semua follow-up sudah diproses."""
        self.pending_followup.status = "COMPLETED"
        self.pending_followup.save()
        html = _pending_meta_oob()
        self.assertIn("0 Pending", html)
        self.assertIn("followup-empty-row", html)
        self.assertIn("hx-swap-oob", html)

    def test_high_priority_listed_before_normal(self):
        """Urutan tampil harus HIGH duluan, baru NORMAL."""
        FollowUp.objects.create(
            vehicle=self.vehicle,
            type="REACTIVATION",
            priority="NORMAL",
            scheduled_at=date.today() - timedelta(days=1),
            status="PENDING",
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("automation:followup_list"))
        rows = response.context["rows"]
        priorities = [row["followup"].priority for row in rows]
        self.assertEqual(priorities, ["HIGH", "NORMAL"])