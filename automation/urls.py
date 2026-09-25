from django.urls import path
from . import views

app_name = "automation"

urlpatterns = [
    path("followups/", views.followup_list, name="followup_list"),
    path("followups/<int:pk>/complete/", views.followup_complete, name="followup_complete"),
    path("followups/<int:pk>/cancel/", views.followup_cancel, name="followup_cancel"),
]