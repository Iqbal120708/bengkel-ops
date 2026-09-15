from django.contrib import admin
from .models import AutomationSetting, FollowUp


@admin.register(AutomationSetting)
class AutomationSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Klasifikasi Kendaraan", {
            "fields": ("inactive_threshold_days", "reactivation_cooldown_days")
        }),
        ("Follow-up Otomatis", {
            "fields": ("new_customer_followup_delay_days",)
        }),
        ("Segmentasi VIP", {
            "fields": ("vip_min_service_count", "vip_min_total_spending")
        }),
        ("Inventory", {
            "fields": ("low_stock_threshold_default",)
        }),
        ("Margin", {
            "fields": ("margin_percentage_default",)
        })
    )
    readonly_fields = ()

    def has_add_permission(self, request):
        return not AutomationSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "type", "priority", "status", "scheduled_at", "completed_at")
    list_filter = ("type", "priority", "status", "scheduled_at")
    search_fields = ("vehicle__plate_number", "vehicle__customer__name", "notes")
    readonly_fields = ("created_at", "completed_at")
    fieldsets = (
        ("Informasi Follow-up", {
            "fields": ("vehicle", "type", "priority", "status")
        }),
        ("Jadwal", {
            "fields": ("scheduled_at", "completed_at")
        }),
        ("Catatan", {
            "fields": ("notes",)
        }),
        ("Metadata", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )
