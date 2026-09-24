from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Customer, Vehicle


@login_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = Customer.objects.all().order_by("name")

    if query:
        customers = customers.filter(
            Q(name__icontains=query) | Q(phone__icontains=query)
        )

    paginator = Paginator(customers, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"page_obj": page_obj, "query": query}

    if request.headers.get("HX-Request"):
        return render(request, "customers/_customer_list_rows.html", context)

    return render(request, "customers/customer_list.html", context)


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        Customer.objects.with_vip_status(), pk=pk
    )
    vehicles = customer.vehicles.all().order_by("-created_at")

    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer, "vehicles": vehicles},
    )


@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    service_records = (
        vehicle.service_records.all()
        .prefetch_related("items__sparepart")
        .order_by("-service_date")
    )
    pending_followup = (
        vehicle.followups.filter(status="PENDING").order_by("-priority").first()
    )
    return render(
        request,
        "customers/vehicle_detail.html",
        {
            "vehicle": vehicle,
            "service_records": service_records,
            "pending_followup": pending_followup,
        },
    )