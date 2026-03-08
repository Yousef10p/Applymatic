from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("apply/", views.apply_view, name="apply"),
    path("guest/test/", views.guest_extract_view, name="guest_extract"), # The new dedicated guest URL
]