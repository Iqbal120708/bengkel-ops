from django.db import models

# Create your models here.
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
    
    def __str__(self):
        return f"{self.customer.name} - {self.model_name} - {self.plate_number}"