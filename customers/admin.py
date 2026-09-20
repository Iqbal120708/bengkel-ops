from django.contrib import admin
from .models import Customer, Vehicle


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 1
    fields = ("plate_number", "brand", "model_name", "vehicle_type", "status", "last_service_date")
    readonly_fields = ("status", "last_service_date")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "vehicle_count", "created_at")
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [VehicleInline]
    fieldsets = (
        ("Informasi Dasar", {
            "fields": ("name", "phone", "email", "address")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def vehicle_count(self, obj):
        return obj.vehicles.count()
    vehicle_count.short_description = "Jumlah Kendaraan"


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "brand", "model_name", "customer", "vehicle_type", "status", "last_service_date")
    list_filter = ("status", "vehicle_type", "created_at")
    search_fields = ("plate_number", "brand", "model_name", "customer__name")
    fieldsets = (
        ("Informasi Kendaraan", {
            "fields": ("customer", "plate_number", "brand", "model_name", "vehicle_type")
        }),
        ("Status & Riwayat", {
            "fields": ("status", "last_service_date", "last_service_odometer"),
            "description": (
                "Dihitung otomatis dari riwayat servis. "
                "bisa tertimpa saat ada ServiceRecord baru/dihapus, atau saat batch job harian jalan."
            ),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if request.user.role == "OWNER":
            return ["created_at", "updated_at"]
        return ["status", "last_service_date", "last_service_odometer", "created_at", "updated_at"]