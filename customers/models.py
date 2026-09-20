from django.db import models
from django.utils import timezone
from automation.models import AutomationSetting

class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class Vehicle(models.Model):
    VEHICLE_TYPE = [("MOTOR", "Motor"), ("MOBIL", "Mobil")]
    STATUS = [("NEW", "New"), ("ACTIVE", "Active"), ("INACTIVE", "Inactive")]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE)
    status = models.CharField(max_length=10, choices=STATUS, default="NEW")
    last_service_date = models.DateField(null=True, blank=True)
    last_service_odometer = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.status in ("ACTIVE", "INACTIVE") and self.last_service_date is None:
            raise ValidationError(
                "Status ACTIVE/INACTIVE butuh Last Service Date diisi juga. "
                "Kalau vehicle belum pernah servis, gunakan status NEW."
            )
        
    def __str__(self):
        return f"{self.customer.name} - {self.model_name} - {self.plate_number}"
    
def recompute_vehicle_status(vehicle):
    """Hitung ulang status, last_service_date, dan last_service_odometer
    Vehicle dari riwayat ServiceRecord yang BENAR-BENAR tersisa saat ini.
    Dipanggil setelah ServiceRecord dihapus."""
    setting = AutomationSetting.objects.first()
    latest = vehicle.service_records.order_by("-service_date").first()

    if latest is None:
        vehicle.status = "NEW"
        vehicle.last_service_date = None
        vehicle.last_service_odometer = None
    else:
        vehicle.last_service_date = latest.service_date
        if latest.odometer is not None:
            vehicle.last_service_odometer = latest.odometer
        # latest.odometer None -> last_service_odometer TIDAK disentuh, tetap nilai lama

        days_since = (timezone.now().date() - latest.service_date).days
        vehicle.status = "INACTIVE" if days_since > setting.inactive_threshold_days else "ACTIVE"

    vehicle.save(update_fields=["status", "last_service_date", "last_service_odometer", "updated_at"])
    return vehicle.status