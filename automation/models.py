from django.db import models

# Create your models here.
class AutomationSetting(models.Model):
    inactive_threshold_days = models.PositiveIntegerField(default=90)
    new_customer_followup_delay_days = models.PositiveIntegerField(default=3)
    reactivation_cooldown_days = models.PositiveIntegerField(default=14)
    vip_min_service_count = models.PositiveIntegerField(default=4)
    vip_min_total_spending = models.DecimalField(max_digits=12, decimal_places=0, default=1500000)
    low_stock_threshold_default = models.PositiveIntegerField(default=5)

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)
        
    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
        
    def __str__(self):
        return "Automation Setting"
        
class FollowUp(models.Model):
    TYPE_CHOICES = [("NEW_CUSTOMER", "New Customer"), ("REACTIVATION", "Reactivation")]
    PRIORITY_CHOICES = [("HIGH", "High"), ("NORMAL", "Normal")]
    STATUS_CHOICES = [("PENDING", "Pending"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")]

    vehicle = models.ForeignKey("customers.Vehicle", on_delete=models.CASCADE, related_name="followups")
    type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    scheduled_at = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)