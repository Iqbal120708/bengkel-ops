from django.db import models

# Create your models here.
class Sparepart(models.Model):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=20)  # pcs, liter, dst
    stock_quantity = models.PositiveIntegerField(default=0)
    minimum_stock_threshold = models.PositiveIntegerField(default=5)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.sku}"