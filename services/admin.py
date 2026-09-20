from django.contrib import admin
from .models import ServiceRecord, ServiceRecordItem


class ServiceRecordItemInline(admin.TabularInline):
    model = ServiceRecordItem
    extra = 1
    fields = ("sparepart", "quantity_used", "price_at_time_of_use")
    raw_id_fields = ("sparepart",)


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    delete_confirmation_template = "admin/services/servicerecord/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/services/servicerecord/delete_selected_confirmation.html"
    
    list_display = ("vehicle", "service_date", "service_type", "cost", "created_by", "created_at")
    list_filter = ("service_date", "service_type", "created_at")
    search_fields = ("vehicle__plate_number", "vehicle__customer__name", "service_type", "notes")
    readonly_fields = ("created_at", "created_by")
    inlines = [ServiceRecordItemInline]
    fieldsets = (
        ("Informasi Servis", {
            "fields": ("vehicle", "service_date", "service_type", "odometer", "cost", "notes")
        }),
        ("Metadata", {
            "fields": ("created_by", "created_at"),
            "classes": ("collapse",)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # create new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
