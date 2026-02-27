from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import google_login, google_callback

app_name = "accounts"

urlpatterns = [
    path("login/", google_login, name="login"),
    path("google/callback/", google_callback, name="callback"),
    path("logout/", LogoutView.as_view(), name="logout"),
]