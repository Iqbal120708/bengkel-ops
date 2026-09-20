from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

from customers.models import Customer, Vehicle, recompute_vehicle_status
from inventory.models import Sparepart
from automation.models import AutomationSetting, FollowUp
from .models import ServiceRecord, ServiceRecordItem


class ServiceRecordSignalTests(TestCase):
    def setUp(self):
        AutomationSetting.objects.create(pk=1)
        customer = Customer.objects.create(name="Andi", phone="0812")
        self.vehicle = Vehicle.objects.create(
            customer=customer, plate_number="D1234AB",
            brand="Honda", model_name="Vario", vehicle_type="MOTOR",
        )

    def test_first_service_activates_vehicle_and_creates_followup(self):
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "ACTIVE")
        self.assertEqual(
            FollowUp.objects.filter(vehicle=self.vehicle, type="NEW_CUSTOMER").count(), 1
        )

    def test_second_service_does_not_create_followup(self):
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Tune Up", cost=100000,
        )
        self.assertEqual(FollowUp.objects.filter(vehicle=self.vehicle).count(), 1)

    def test_inactive_vehicle_reactivates_without_new_followup(self):
        self.vehicle.status = "INACTIVE"
        self.vehicle.save()
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Servis Besar", cost=200000,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "ACTIVE")
        self.assertEqual(FollowUp.objects.filter(vehicle=self.vehicle).count(), 1)

    def test_edit_service_record_has_no_side_effect(self):
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        followup_count_before = FollowUp.objects.count()
        sr.cost = 60000
        sr.save()
        self.assertEqual(FollowUp.objects.count(), followup_count_before)


class ServiceRecordItemSignalTests(TestCase):
    def setUp(self):
        AutomationSetting.objects.create(pk=1)
        customer = Customer.objects.create(name="Budi", phone="0813")
        vehicle = Vehicle.objects.create(
            customer=customer, plate_number="D5678CD",
            brand="Yamaha", model_name="NMAX", vehicle_type="MOTOR",
        )
        self.service_record = ServiceRecord.objects.create(
            vehicle=vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        self.sparepart = Sparepart.objects.create(
            name="Oli Mesin", sku="OLI-001", unit="liter",
            stock_quantity=10, price=45000,
        )

    def test_create_item_decrements_stock(self):
        ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        self.sparepart.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 8)

    def test_edit_same_quantity_no_change(self):
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        item.price_at_time_of_use = 47000  # field lain berubah, quantity_used tetap
        item.save()
        self.sparepart.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 8)

    def test_edit_quantity_increase_decrements_delta_only(self):
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        item.quantity_used = 3
        item.save()
        self.sparepart.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 7)  # bukan 5

    def test_edit_quantity_decrease_restores_delta_only(self):
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=3, price_at_time_of_use=45000,
        )
        item.quantity_used = 1
        item.save()
        self.sparepart.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 9)  # 10-3+2

    def test_cannot_change_sparepart_on_existing_item(self):
        other_sparepart = Sparepart.objects.create(
            name="Filter Oli", sku="FIL-001", unit="pcs",
            stock_quantity=5, price=30000,
        )
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        item.sparepart = other_sparepart
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_delete_item_restores_stock(self):
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        item.delete()
        self.sparepart.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 10)

    def test_cascade_delete_service_record_restores_all_items_stock(self):
        sparepart_2 = Sparepart.objects.create(
            name="Busi", sku="BSI-001", unit="pcs",
            stock_quantity=20, price=15000,
        )
        ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=sparepart_2,
            quantity_used=4, price_at_time_of_use=15000,
        )
        self.service_record.delete()
        self.sparepart.refresh_from_db()
        sparepart_2.refresh_from_db()
        self.assertEqual(self.sparepart.stock_quantity, 10)
        self.assertEqual(sparepart_2.stock_quantity, 20)

    def test_over_quantity_raises_integrity_error(self):
        from django.db import IntegrityError
        item = ServiceRecordItem.objects.create(
            service_record=self.service_record, sparepart=self.sparepart,
            quantity_used=2, price_at_time_of_use=45000,
        )
        item.quantity_used = 999
        with self.assertRaises(IntegrityError):
            item.save()

class RecomputeVehicleStatusTests(TestCase):
    def setUp(self):
        AutomationSetting.objects.create(pk=1, inactive_threshold_days=90)
        customer = Customer.objects.create(name="Citra", phone="0814")
        self.vehicle = Vehicle.objects.create(
            customer=customer, plate_number="D9999XY",
            brand="Honda", model_name="Beat", vehicle_type="MOTOR",
        )

    def test_delete_only_record_reverts_to_new(self):
        """Hapus satu-satunya ServiceRecord vehicle -> status balik NEW, last_service_date/odometer kosong."""
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        sr.delete()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "NEW")
        self.assertIsNone(self.vehicle.last_service_date)
        self.assertIsNone(self.vehicle.last_service_odometer)

    def test_delete_recent_record_reverts_to_older_active(self):
        """Hapus record terbaru, masih ada record lama dalam threshold -> status tetap ACTIVE, data balik ke record lama."""
        old_date = timezone.now().date() - timedelta(days=10)
        recent_date = timezone.now().date()
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=old_date,
            service_type="Ganti Oli", cost=50000, odometer=1000,
        )
        recent = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=recent_date,
            service_type="Tune Up", cost=100000, odometer=1200,
        )
        recent.delete()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "ACTIVE")
        self.assertEqual(self.vehicle.last_service_date, old_date)
        self.assertEqual(self.vehicle.last_service_odometer, 1000)

    def test_delete_reactivating_record_reverts_to_inactive(self):
        """Hapus record yang bikin vehicle ACTIVE lagi, record lama yang tersisa sudah lewat threshold -> status balik INACTIVE."""
        old_date = timezone.now().date() - timedelta(days=120)  # > threshold 90
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=old_date,
            service_type="Ganti Oli", cost=50000,
        )
        # simulasikan hasil batch job kemarin (Langkah 4 belum ada batch job, jadi diset manual)
        self.vehicle.status = "INACTIVE"
        self.vehicle.save(update_fields=["status"])

        reactivating = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Servis Besar", cost=200000,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "ACTIVE")

        reactivating.delete()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "INACTIVE")
        self.assertEqual(self.vehicle.last_service_date, old_date)

    def test_delete_does_not_touch_existing_followup(self):
        """Hapus ServiceRecord -> FollowUp yang sudah ada (status apapun) tidak ikut berubah/terhapus."""
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        followup = FollowUp.objects.get(vehicle=self.vehicle, type="NEW_CUSTOMER")
        sr.delete()
        self.assertTrue(FollowUp.objects.filter(pk=followup.pk).exists())
        followup.refresh_from_db()
        self.assertEqual(followup.status, "PENDING")


class ServiceRecordUpdateSignalTests(TestCase):
    def setUp(self):
        AutomationSetting.objects.create(pk=1, inactive_threshold_days=90)
        customer = Customer.objects.create(name="Dedi", phone="0815")
        self.vehicle = Vehicle.objects.create(
            customer=customer, plate_number="D1111ZZ",
            brand="Yamaha", model_name="Mio", vehicle_type="MOTOR",
        )

    def test_edit_latest_record_date_propagates_to_vehicle(self):
        """Edit tanggal record yang memang terbaru -> last_service_date vehicle ikut berubah."""
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000, odometer=5000,
        )
        new_date = timezone.now().date() + timedelta(days=1)
        sr.service_date = new_date
        sr.odometer = 5100
        sr.save()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_date, new_date)
        self.assertEqual(self.vehicle.last_service_odometer, 5100)

    def test_edit_older_record_does_not_overwrite_vehicle(self):
        """Edit record yang BUKAN terbaru -> last_service_date/odometer vehicle tetap dari record terbaru."""
        older = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date() - timedelta(days=10),
            service_type="Ganti Oli", cost=50000, odometer=1000,
        )
        newer = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Tune Up", cost=100000, odometer=1200,
        )
        older.cost = 60000  # edit field lain, bukan tanggal
        older.save()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_date, newer.service_date)
        self.assertEqual(self.vehicle.last_service_odometer, 1200)

    def test_edit_makes_older_record_become_latest(self):
        """Ubah tanggal record lama jadi lebih baru dari yang sekarang terbaru -> vehicle ikut pindah acuan."""
        record_a = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date() - timedelta(days=5),
            service_type="Ganti Oli", cost=50000, odometer=1000,
        )
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Tune Up", cost=100000, odometer=1200,
        )
        record_a.service_date = timezone.now().date() + timedelta(days=1)
        record_a.odometer = 1300
        record_a.save()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_date, record_a.service_date)
        self.assertEqual(self.vehicle.last_service_odometer, 1300)

    def test_odometer_none_on_create_does_not_clear_existing_value(self):
        """Record terbaru dibuat tanpa odometer -> last_service_odometer TIDAK ditimpa jadi None."""
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date() - timedelta(days=1),
            service_type="Ganti Oli", cost=50000, odometer=1000,
        )
        ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Cuci Motor", cost=15000, odometer=None,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_odometer, 1000)  # tetap dari record sebelumnya

    def test_cannot_clear_existing_odometer_via_edit(self):
        """Odometer yang sudah ada nilainya tidak boleh diedit jadi None -- clean() harus reject."""
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000, odometer=2000,
        )
        sr.odometer = None
        with self.assertRaises(ValidationError):
            sr.full_clean()

    def test_edit_does_not_create_duplicate_followup(self):
        """Edit record pertama (bukan create baru) -> tidak ikut trigger FollowUp lagi."""
        sr = ServiceRecord.objects.create(
            vehicle=self.vehicle, service_date=timezone.now().date(),
            service_type="Ganti Oli", cost=50000,
        )
        sr.cost = 55000
        sr.save()
        self.assertEqual(
            FollowUp.objects.filter(vehicle=self.vehicle, type="NEW_CUSTOMER").count(), 1
        )