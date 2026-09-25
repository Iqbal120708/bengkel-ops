from datetime import timedelta

from django.db.models import Prefetch, Case, When, IntegerField, F
from django.utils import timezone

from automation.models import FollowUp
from customers.models import Customer
from inventory.models import Sparepart
from customers.models import Vehicle
from services.models import ServiceRecord

DASHBOARD_PRIORITY_LIMIT = 10
FOLLOWUP_PER_PAGE = 20


def get_pending_followups_ordered():
    """
    Base queryset PENDING follow-up, urut priority HIGH dulu lalu scheduled_at.
    Dipakai dashboard (di-slice) dan FollowUp list (di-paginate) — satu sumber,
    jangan ditulis ulang di tempat lain.
    """
    return FollowUp.objects.filter(status="PENDING").select_related(
        "vehicle"
    ).prefetch_related(
        Prefetch("vehicle__customer", queryset=Customer.objects.with_vip_status())
    ).annotate(
        priority_order=Case(
            When(priority="HIGH", then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("priority_order", "scheduled_at")


def get_priority_followups():
    return get_pending_followups_ordered()[:DASHBOARD_PRIORITY_LIMIT]


def get_dashboard_stats():
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    return {
        "kendaraan_terdaftar": Vehicle.objects.count(),
        "servis_bulan_ini": ServiceRecord.objects.filter(
            service_date__gte=start_of_month
        ).count(),
        "perlu_followup": FollowUp.objects.filter(status="PENDING").count(),
        "stok_kritis": Sparepart.objects.filter(
            stock_quantity__lte=F("minimum_stock_threshold")
        ).count(),
        "vip_customers": Customer.objects.with_vip_status().filter(is_vip=True).count(),
    }


def get_today_actions():
    pending_qs = FollowUp.objects.filter(status="PENDING")
    return {
        "followup_pending": pending_qs.count(),
        "priority_tinggi": pending_qs.filter(priority="HIGH").count(),
        "stok_kritis": Sparepart.objects.filter(
            stock_quantity__lte=F("minimum_stock_threshold")
        ).count(),
    }