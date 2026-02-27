from django.contrib import admin
from .models import GoogleOAuthProfile

@admin.register(GoogleOAuthProfile)
class GoogleOAuthProfileAdmin(admin.ModelAdmin):
    # Display the related user and check if we successfully captured a refresh token
    list_display = ('get_user_email', 'has_refresh_token')
    search_fields = ('user__email',)

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'User Email'
    get_user_email.admin_order_field = 'user__email'

    def has_refresh_token(self, obj):
        # Returns a nice boolean checkmark in the admin panel
        return bool(obj.refresh_token)
    has_refresh_token.boolean = True
    has_refresh_token.short_description = 'Has Refresh Token?'