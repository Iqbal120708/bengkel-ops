from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from automation.models import AutomationSetting, FollowUp
from inventory.models import Sparepart
from .models import ServiceRecord, ServiceRecordItem
from customers.models import recompute_vehicle_status

@receiver(post_save, sender=ServiceRecord)
def handle_service_record_saved(sender, instance, created, **kwargs):
    vehicle = instance.vehicle
    is_first_service = created and vehicle.service_records.count() == 1

    recompute_vehicle_status(vehicle)

    if is_first_service:
        setting = AutomationSetting.objects.get(pk=1)
        FollowUp.objects.create(
            vehicle=vehicle,
            type="NEW_CUSTOMER",
            scheduled_at=timezone.now().date() + timezone.timedelta(
                days=setting.new_customer_followup_delay_days
            ),
        )

@receiver(pre_save, sender=ServiceRecordItem)
def capture_old_quantity(sender, instance, **kwargs):
    if instance.pk:
        instance._old_quantity_used = (
            ServiceRecordItem.objects
            .filter(pk=instance.pk)
            .values_list("quantity_used", flat=True)
            .first() or 0
        )
    else:
        instance._old_quantity_used = 0


@receiver(post_save, sender=ServiceRecordItem)
def apply_stock_delta(sender, instance, created, **kwargs):
    old_qty = getattr(instance, "_old_quantity_used", 0)
    delta = old_qty - instance.quantity_used  # positif = kembalikan, negatif = kurangi
    if delta != 0:
        Sparepart.objects.filter(pk=instance.sparepart_id).update(
            stock_quantity=F("stock_quantity") + delta
        )


@receiver(post_delete, sender=ServiceRecordItem)
def restore_stock_on_delete(sender, instance, **kwargs):
    Sparepart.objects.filter(pk=instance.sparepart_id).update(
        stock_quantity=F("stock_quantity") + instance.quantity_used
    )


@receiver(post_delete, sender=ServiceRecord)
def handle_service_record_deleted(sender, instance, **kwargs):
    recompute_vehicle_status(instance.vehicle)