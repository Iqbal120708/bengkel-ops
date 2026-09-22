from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model
from automation.models import AutomationSetting
from customers.models import Customer, Vehicle
from inventory.models import Sparepart

from .admin import ServiceRecordItemInline
from .models import ServiceRecord, ServiceRecordItem

User = get_user_model()

class BaseServiceTestCase(TestCase):
    """Data dummy bersama: 1 vehicle, 2 sparepart, 1 kasir dengan permission, 1 tanpa permission."""

    @classmethod
    def setUpTestData(cls):
        AutomationSetting.objects.get_or_create(pk=1)

        cls.customer = Customer.objects.create(name="Andi", phone="0812345678")
        cls.vehicle = Vehicle.objects.create(
            customer=cls.customer,
            plate_number="E 1234 AB",
            brand="Honda",
            model_name="Vario",
            vehicle_type="MOTOR",
        )
        cls.oli = Sparepart.objects.create(
            name="Oli MPX2", sku="OLI-1", unit="pcs",
            stock_quantity=100, minimum_stock_threshold=5,
            price=Decimal("35000"),
        )
        cls.filter = Sparepart.objects.create(
            name="Filter Oli", sku="FLT-1", unit="pcs",
            stock_quantity=100, minimum_stock_threshold=5,
            price=Decimal("20000"),
        )

        cls.kasir = User.objects.create_user(
            username="kasir", password="x", role="ADMIN"
        )
        cls.kasir.is_staff = True
        cls.kasir.is_superuser = True
        cls.kasir.save()

        cls.no_perm = User.objects.create_user(
            username="noperm", password="x", role="ADMIN"
        )
        cls.no_perm.is_staff = True
        cls.no_perm.save()

    def make_record(self):
        """ServiceRecord kosong (cost=0) sebagai FK untuk test item."""
        return ServiceRecord.objects.create(
            vehicle=self.vehicle,
            service_date=date.today(),
            service_type="Ganti oli",
            cost=Decimal("0"),
        )


class ServiceRecordItemPriceTests(BaseServiceTestCase):
    """Perilaku auto-fill price_at_time_of_use dari Sparepart.price."""

    def test_price_filled_from_sparepart_when_empty(self):
        """Harga kosong saat create -> otomatis diisi dari sparepart.price."""
        item = ServiceRecordItem(
            service_record=self.make_record(),
            sparepart=self.oli,
            quantity_used=2,
        )
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.price_at_time_of_use, Decimal("35000"))

    def test_explicit_price_is_kept(self):
        """Harga yang diisi manual saat create tidak ditimpa."""
        item = ServiceRecordItem.objects.create(
            service_record=self.make_record(),
            sparepart=self.oli,
            quantity_used=1,
            price_at_time_of_use=Decimal("30000"),
        )
        self.assertEqual(item.price_at_time_of_use, Decimal("30000"))

    def test_price_is_snapshot_not_affected_by_later_sparepart_change(self):
        """Harga tersimpan adalah snapshot, tidak ikut berubah saat Sparepart.price berubah belakangan."""
        item = ServiceRecordItem.objects.create(
            service_record=self.make_record(),
            sparepart=self.oli,
            quantity_used=1,
        )
        self.oli.price = Decimal("50000")
        self.oli.save()

        item.refresh_from_db()
        self.assertEqual(item.price_at_time_of_use, Decimal("35000"))

    def test_edited_price_on_existing_item_is_persisted(self):
        """Harga yang diedit manual pada item lama (halaman update) tersimpan sesuai input."""
        item = ServiceRecordItem.objects.create(
            service_record=self.make_record(),
            sparepart=self.oli,
            quantity_used=1,
        )
        item.price_at_time_of_use = Decimal("40000")
        item.save()

        item.refresh_from_db()
        self.assertEqual(item.price_at_time_of_use, Decimal("40000"))

    def test_blank_price_on_existing_item_falls_back_to_sparepart_price(self):
        """Harga item lama yang sengaja dikosongkan lagi -> jatuh kembali ke sparepart.price."""
        item = ServiceRecordItem.objects.create(
            service_record=self.make_record(),
            sparepart=self.oli,
            quantity_used=1,
            price_at_time_of_use=Decimal("40000"),
        )
        item.price_at_time_of_use = None
        item.save()

        item.refresh_from_db()
        self.assertEqual(item.price_at_time_of_use, Decimal("35000"))


class InlineFieldsTests(BaseServiceTestCase):
    """Field price_at_time_of_use tersembunyi di halaman add, tampil dan bisa diedit di halaman change."""

    def setUp(self):
        self.inline = ServiceRecordItemInline(ServiceRecord, admin.site)
        self.request = RequestFactory().get("/")

    def test_price_field_hidden_on_add(self):
        """obj=None (halaman add) -> kolom harga tidak ada di form."""
        fields = self.inline.get_fields(self.request, obj=None)
        self.assertNotIn("price_at_time_of_use", fields)

    def test_price_field_shown_on_change(self):
        """obj terisi (halaman change) -> kolom harga muncul."""
        fields = self.inline.get_fields(self.request, obj=self.make_record())
        self.assertIn("price_at_time_of_use", fields)

    def test_price_field_is_not_readonly(self):
        """Kolom harga yang muncul di halaman change harus bisa diedit, bukan readonly."""
        self.assertNotIn("price_at_time_of_use", self.inline.readonly_fields)


class CalculateCostViewTests(BaseServiceTestCase):
    """Endpoint AJAX tombol 'Hitung': parts_total + labor, dengan berbagai kasus input."""

    def setUp(self):
        self.url = reverse("admin:services_servicerecord_calculate_cost")
        self.client.force_login(self.kasir)

    def calc(self, rows=(), labor=""):
        return self.client.get(self.url, {"row": list(rows), "labor": labor})

    def row(self, sparepart, qty, price=""):
        return f"{sparepart.pk},{qty},{price}"

    def test_anonymous_is_redirected_to_login(self):
        """User belum login diarahkan ke halaman login admin, bukan diberi data."""
        self.client.logout()
        response = self.calc()
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_user_without_view_permission_gets_403(self):
        """User staff tanpa permission view ServiceRecord ditolak dengan 403."""
        self.client.force_login(self.no_perm)
        response = self.calc()
        self.assertEqual(response.status_code, 403)

    def test_parts_only(self):
        """Tanpa labor, cost = jumlah harga sparepart × qty."""
        response = self.calc([self.row(self.oli, 2)])
        self.assertEqual(response.json()["cost"], "70000")

    def test_multiple_rows_and_labor(self):
        """Beberapa baris sparepart + labor dijumlahkan dengan benar."""
        response = self.calc(
            [self.row(self.oli, 1), self.row(self.filter, 3)],
            labor="25000",
        )
        # 35000 + 3 * 20000 + 25000
        self.assertEqual(response.json()["cost"], "120000")
        self.assertEqual(response.json()["parts_total"], "95000")

    def test_labor_only_service_without_parts(self):
        """Servis tanpa sparepart (misal setel rem) tetap menghasilkan cost dari labor saja."""
        response = self.calc(labor="50000")
        self.assertEqual(response.json()["cost"], "50000")

    def test_form_price_overrides_sparepart_price(self):
        """Harga yang sedang diedit di form (baris lama) dipakai, bukan harga sparepart saat ini."""
        response = self.calc([self.row(self.oli, 2, price="30000")])
        self.assertEqual(response.json()["cost"], "60000")

    def test_zero_or_empty_price_falls_back_to_sparepart_price(self):
        """Harga kosong atau 0 di form dianggap 'belum diisi' -> pakai harga sparepart."""
        for price in ("", "0"):
            with self.subTest(price=price):
                response = self.calc([self.row(self.oli, 1, price=price)])
                self.assertEqual(response.json()["cost"], "35000")

    def test_unknown_sparepart_id_is_ignored(self):
        """ID sparepart yang tidak ada di database dilewati, bukan bikin error."""
        response = self.calc(["99999,1,"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cost"], "0")

    def test_zero_quantity_and_malformed_rows_are_skipped(self):
        """Qty 0 dan baris yang formatnya rusak dilewati diam-diam, tidak bikin request gagal."""
        rows = [self.row(self.oli, 0), "abc", "1,2", ",,"]
        response = self.calc(rows)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cost"], "0")

    def test_invalid_price_returns_400(self):
        """Harga yang bukan angka (typo) mengembalikan error, bukan diam-diam dianggap 0."""
        response = self.calc([self.row(self.oli, 1, price="abc")])
        self.assertEqual(response.status_code, 400)

    def test_invalid_labor_returns_400(self):
        """Labor yang bukan angka mengembalikan error, bukan diam-diam dianggap 0."""
        response = self.calc(labor="abc")
        self.assertEqual(response.status_code, 400)

    def test_cost_has_no_decimal_part(self):
        """Hasil cost berupa bilangan bulat, tidak ada '.00' di belakang koma."""
        response = self.calc([self.row(self.oli, 1)], labor="10000")
        self.assertNotIn(".", response.json()["cost"])


class AdminAddFlowTests(BaseServiceTestCase):
    """Alur end-to-end submit form add ServiceRecord + item lewat Django admin."""

    def test_add_record_with_item_without_price_uses_sparepart_price(self):
        """Submit form add tanpa mengisi harga item -> tersimpan pakai harga sparepart saat itu."""
        self.client.force_login(self.kasir)
        data = {
            "vehicle": self.vehicle.pk,
            "service_date": "2026-09-21",
            "service_type": "Ganti oli",
            "labor_fee": "15000",
            "cost": "85000",
            "notes": "",
            # hapus baris ini kalau created_by tidak ada di form admin kamu
            "created_by": self.kasir.pk,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": "",
            "items-0-service_record": "",
            "items-0-sparepart": self.oli.pk,
            "items-0-quantity_used": "2",
        }
        response = self.client.post(reverse("admin:services_servicerecord_add"), data)

        # 302 = sukses. Kalau 200, ada error form: lihat
        # response.context["adminform"].form.errors dan response.context["inline_admin_formsets"]
        self.assertEqual(response.status_code, 302)

        item = ServiceRecordItem.objects.get(sparepart=self.oli, quantity_used=2)
        self.assertEqual(item.price_at_time_of_use, Decimal("35000"))
        self.assertEqual(item.service_record.cost, Decimal("85000"))
        self.assertEqual(item.service_record.labor_fee, Decimal("15000"))