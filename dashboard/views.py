from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import role_required 
from dashboard.services import (
    get_dashboard_stats,
    get_today_actions,
    get_priority_followups,
)


@login_required
@role_required("OWNER", "ADMIN")
def dashboard_view(request):
    context = {
        "stats": get_dashboard_stats(),
        "today_actions": get_today_actions(),
        "priority_followups": get_priority_followups(),
    }
    return render(request, "dashboard/index.html", context)