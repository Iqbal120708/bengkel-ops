from django.contrib import admin
from .models import Sparepart


@admin.register(Sparepart)
class SparepartAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "stock_quantity", "minimum_stock_threshold", "stock_status", "price", "created_at")
    list_filter = ("created_at", "unit")
    search_fields = ("name", "sku")
    readonly_fields = ("created_at", "updated_at", "stock_status")
    fieldsets = (
        ("Informasi Sparepart", {
            "fields": ("name", "sku", "unit", "price")
        }),
        ("Inventory", {
            "fields": ("stock_quantity", "minimum_stock_threshold", "stock_status")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def stock_status(self, obj):
        if obj.stock_quantity <= obj.minimum_stock_threshold:
            return f"KRITIS ({obj.stock_quantity})"
        return f"OK ({obj.stock_quantity})"
    stock_status.short_description = "Status Stok"
