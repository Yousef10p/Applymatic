from django.urls import path
from .views import landing_view, start_guest, apply_view

app_name = "core"

urlpatterns = [
    path("", landing_view, name="landing"),
    path("guest/start/", start_guest, name="start_guest"),
    path("apply/", apply_view, name="apply"),
]