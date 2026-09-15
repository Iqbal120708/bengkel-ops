from django.db import models
from django.contrib.auth import get_user_model
from automation.models import AutomationSetting

User = get_user_model()

# Create your models here.
class ServiceRecord(models.Model):
    vehicle = models.ForeignKey("customers.Vehicle", on_delete=models.CASCADE, related_name="service_records")
    service_date = models.DateField()
    service_type = models.CharField(max_length=100)  # bisa upgrade ke FK predefined list nanti
    odometer = models.PositiveIntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def total_sparepart_cost(self):
        return sum(
            item.quantity_used * item.price_at_time_of_use 
            for item in self.items.all()
        )

    @property
    def calculate_cost(self):
        margin_percentage = AutomationSetting.objects.first().margin_percentage_default
        return self.total_sparepart_cost * (1 + margin_percentage / 100)
    
class ServiceRecordItem(models.Model):
    service_record = models.ForeignKey(ServiceRecord, on_delete=models.CASCADE, related_name="items")
    sparepart = models.ForeignKey("inventory.Sparepart", on_delete=models.PROTECT)
    quantity_used = models.PositiveIntegerField()
    price_at_time_of_use = models.DecimalField(max_digits=12, decimal_places=2)