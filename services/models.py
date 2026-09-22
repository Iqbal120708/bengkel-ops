from django.db import models
from django.contrib.auth import get_user_model
from automation.models import AutomationSetting
from django.core.exceptions import ValidationError

User = get_user_model()

# Create your models here.
class ServiceRecord(models.Model):
    vehicle = models.ForeignKey("customers.Vehicle", on_delete=models.CASCADE, related_name="service_records")
    service_date = models.DateField()
    service_type = models.CharField(max_length=100)  # bisa upgrade ke FK predefined list nanti
    odometer = models.PositiveIntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    labor_fee = models.DecimalField(
        "Biaya jasa", max_digits=12, decimal_places=0, default=0
    )

    def clean(self):
        if self.pk:
            old_odometer = (
                ServiceRecord.objects
                .filter(pk=self.pk)
                .values_list("odometer", flat=True)
                .first()
            )
            if old_odometer is not None and self.odometer is None:
                raise ValidationError(
                    "Odometer yang sudah diisi tidak boleh dikosongkan. "
                    "Edit ke angka yang benar, jangan dihapus."
                )
    
    def __str__(self, *args, **kwargs):
        return f"{self.vehicle.model_name} - {self.service_date}"
    
class ServiceRecordItem(models.Model):
    service_record = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name="items")
    sparepart = models.ForeignKey("inventory.Sparepart", on_delete=models.PROTECT)
    quantity_used = models.PositiveIntegerField()
    price_at_time_of_use = models.DecimalField(max_digits=12, decimal_places=0)
    
    def clean(self):
        if self.pk:
            original_sparepart_id = (
                ServiceRecordItem.objects
                .filter(pk=self.pk)
                .values_list("sparepart_id", flat=True)
                .first()
            )
            if original_sparepart_id is not None and original_sparepart_id != self.sparepart_id:
                raise ValidationError(
                    "Sparepart tidak bisa diganti pada item yang sudah ada. Hapus item ini, lalu tambah baru."
                )
                
        if not (self.sparepart_id and self.quantity_used):
            return
        available = self.sparepart.stock_quantity
        if self.pk:
            # sedang edit item lama — kembalikan dulu quantity lama sebelum cek
            old_qty = ServiceRecordItem.objects.get(pk=self.pk).quantity_used
            available += old_qty
        if self.quantity_used > available:
            raise ValidationError(
                f"Stok {self.sparepart.name} tidak cukup (tersedia {available}, diminta {self.quantity_used})"
            )
            
    def save(self, *args, **kwargs):
        if self.price_at_time_of_use is None:
            self.price_at_time_of_use = self.sparepart.price
        super().save(*args, **kwargs)
        
    def __str__(self, *args, **kwargs):
        return f"{self.sparepart.name}"