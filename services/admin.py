from django.contrib import admin
from .models import ServiceRecord, ServiceRecordItem
from django import forms
from django.urls import path, reverse
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from inventory.models import Sparepart

def _to_decimal(value):
    """Kosong dianggap 0, nilai tidak valid dikembalikan None."""
    try:
        return Decimal(value) if value else Decimal("0")
    except InvalidOperation:
        return None

class ServiceRecordItemForm(forms.ModelForm):
    class Meta:
        model = ServiceRecordItem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        price = self.fields.get("price_at_time_of_use")
        if price:
            price.required = False
            price.widget.attrs["placeholder"] = "otomatis"

class ServiceRecordItemInline(admin.TabularInline):
    model = ServiceRecordItem
    extra = 1
    raw_id_fields = ("sparepart",)
    
    def get_fields(self, request, obj=None):
        fields = ["sparepart", "quantity_used"]
        if obj is not None:
            # halaman edit: kolom harga tampil dan bisa diedit
            fields.append("price_at_time_of_use")
        return fields



@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    delete_confirmation_template = "admin/services/servicerecord/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/services/servicerecord/delete_selected_confirmation.html"
    
    list_display = ("vehicle", "service_date", "service_type", "labor_fee", "cost", "created_by", "created_at")
    list_filter = ("service_date", "service_type", "created_at")
    search_fields = ("vehicle__plate_number", "vehicle__customer__name", "service_type", "notes")
    readonly_fields = ("created_at", "created_by")
    inlines = [ServiceRecordItemInline]
    fieldsets = (
        ("Informasi Servis", {
            "fields": ("vehicle", "service_date", "service_type", "odometer", "labor_fee", "cost", "notes")
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


    class Media:
        js = ("services/admin/calc_cost.js",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "cost":
            field.widget.attrs["data-calc-url"] = reverse(
                "admin:services_servicerecord_calculate_cost"
            )
        return field

    def get_urls(self):
        custom = [
            path(
                "calculate-cost/",
                self.admin_site.admin_view(self.calculate_cost_view),
                name="services_servicerecord_calculate_cost",
            ),
        ]
        return custom + super().get_urls()

    def calculate_cost_view(self, request):
        if not self.has_view_permission(request):
            return JsonResponse({"error": "Forbidden"}, status=403)
    
        labor = _to_decimal(request.GET.get("labor", ""))
        if labor is None:
            return JsonResponse({"error": "Biaya jasa tidak valid"}, status=400)
    
        parts_total = Decimal("0")
        for row in request.GET.getlist("row"):
            try:
                sparepart_id, qty, price_raw = row.split(",")
                qty = int(qty)
            except ValueError:
                continue
            if qty <= 0 or not sparepart_id.isdigit():
                continue
    
            price = _to_decimal(price_raw) if price_raw else None
            if price is None and price_raw:
                return JsonResponse({"error": "Harga tidak valid"}, status=400)
            if price is None or price == 0:
                price = (
                    Sparepart.objects.filter(pk=sparepart_id)
                    .values_list("price", flat=True)
                    .first()
                )
            if price is None:  # ID sparepart yang diketik tidak ada
                continue
            parts_total += price * qty
    
        cost = parts_total + labor
        return JsonResponse({"parts_total": str(parts_total), "cost": f"{cost.0f}"})