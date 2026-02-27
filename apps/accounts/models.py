from django.db import models
from django.contrib.auth.models import User
from google.oauth2.credentials import Credentials
from django.conf import settings


class GoogleOAuthProfile(models.Model):
    # Links this profile to the standard Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='googleoauthprofile')

    # We use TextField because Google tokens can be quite long
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)

    def get_credentials(self):
        """Converts the stored text tokens back into a Google Credentials object."""
        return Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

    def __str__(self):
        return f"OAuth Profile for {self.user.email}"