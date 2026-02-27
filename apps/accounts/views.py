import os
import requests
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import GoogleOAuthProfile

# Make sure you have this in your environment/settings for local testing!
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def google_login(request):
    """Step 1: Redirect user to Google's consent screen."""
    # We are asking for basic profile info PLUS permission to send emails
    scopes = "openid email profile https://www.googleapis.com/auth/gmail.send"

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"scope={scopes}&"
        f"access_type=offline&"  # Forces Google to give us a refresh token
        f"prompt=consent"  # Forces consent screen so refresh token is always sent
    )
    return redirect(auth_url)


def google_callback(request):
    """Step 2: Google redirects back here with a code. We exchange it for tokens."""
    code = request.GET.get('code')
    if not code:
        return redirect('core:landing')

    # Exchange the code for tokens
    token_response = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).json()

    access_token = token_response.get('access_token')
    refresh_token = token_response.get('refresh_token')  # Only appears if prompt=consent
    id_token = token_response.get('id_token')

    if not access_token:
        return redirect('core:landing')

    # Get the user's email from Google to log them in
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    email = user_info.get("email")

    # Get or create the Django user
    user, created = User.objects.get_or_create(username=email, defaults={'email': email})

    # Get or create the OAuth Profile and save the tokens!
    profile, profile_created = GoogleOAuthProfile.objects.get_or_create(user=user)
    profile.access_token = access_token
    # Only overwrite refresh_token if Google actually sent a new one
    if refresh_token:
        profile.refresh_token = refresh_token
    profile.save()

    # Log the user in and redirect to the Apply page
    login(request, user)
    return redirect('core:apply')