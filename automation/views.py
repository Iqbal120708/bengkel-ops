import re
from datetime import date
from urllib.parse import quote

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import Case, When, Value, IntegerField
from django.utils import timezone
from django.http import HttpResponse

from accounts.decorators import role_required
from .models import FollowUp

def _followup_context(fu: FollowUp) -> dict:
    vehicle = fu.vehicle
    customer = vehicle.customer

    if fu.type == "NEW_CUSTOMER":
        reason = f"Servis pertama pada {vehicle.last_service_date:%d %b %Y}"
        message = (
            f"Halo {customer.name}, terima kasih sudah servis "
            f"{vehicle.brand} {vehicle.model_name} ({vehicle.plate_number}) "
            f"di bengkel kami. Bagaimana kondisinya sekarang?"
        )
    else:
        days = (date.today() - vehicle.last_service_date).days
        reason = f"Belum servis {days} hari"
        message = (
            f"Halo {customer.name}, sudah {days} hari sejak servis terakhir "
            f"{vehicle.brand} {vehicle.model_name} ({vehicle.plate_number}). "
            f"Yuk jadwalkan servis berikutnya."
        )

    wa_number = customer.phone.as_e164.lstrip("+")
    wa_link = f"https://wa.me/{wa_number}?text={quote(message)}"

    return {
        "followup": fu,
        "customer": customer,
        "vehicle": vehicle,
        "reason": reason,
        "wa_link": wa_link,
    }

def _pending_meta_oob():
    remaining = FollowUp.objects.filter(status="PENDING").count()
    count_html = (
        f'<span id="followup-count" hx-swap-oob="true" '
        f'class="text-sm text-gray-500">{remaining} Pending</span>'
    )
    empty_html = ""
    if remaining == 0:
        empty_html = """
            <table><tbody>
                <tr id="followup-empty-row" hx-swap-oob="true">
                    <td colspan="5" class="py-4 text-center text-gray-400">Belum ada follow-up pending.</td>
                </tr>
            </tbody></table>
        """
    return count_html + empty_html

@role_required("OWNER", "ADMIN")
def followup_list(request):
    qs = (
        FollowUp.objects.filter(status="PENDING")
        .select_related("vehicle", "vehicle__customer")
        .annotate(
            priority_order=Case(
                When(priority="HIGH", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("priority_order", "scheduled_at")
    )
    rows = [_followup_context(fu) for fu in qs]
    return render(request, "automation/followup_list.html", {"rows": rows})


@require_POST
@role_required("OWNER", "ADMIN")
def followup_complete(request, pk):
    fu = get_object_or_404(FollowUp, pk=pk, status="PENDING")
    fu.status = "COMPLETED"
    fu.completed_at = timezone.now()
    fu.save(update_fields=["status", "completed_at"])
    return HttpResponse(_pending_meta_oob())


@require_POST
@role_required("OWNER", "ADMIN")
def followup_cancel(request, pk):
    fu = get_object_or_404(FollowUp, pk=pk, status="PENDING")
    fu.status = "CANCELLED"
    fu.save(update_fields=["status"])
    return HttpResponse(_pending_meta_oob())