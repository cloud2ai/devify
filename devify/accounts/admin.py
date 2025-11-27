from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from accounts.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin interface for Profile model"""

    list_display = [
        'user',
        'registration_completed',
        'language',
        'timezone',
        'nickname',
        'user_date_joined'
    ]
    list_filter = [
        'registration_completed',
        'language',
        'timezone',
        'user__date_joined'
    ]
    search_fields = [
        'user__username',
        'user__email',
        'nickname',
        'registration_token'
    ]
    readonly_fields = [
        'user_date_joined'
    ]
    ordering = ['-user__date_joined']
    list_per_page = 25

    fieldsets = (
        (_('User Information'), {
            'fields': ('user', 'user_date_joined')
        }),
        (_('Registration Status'), {
            'fields': (
                'registration_completed',
                'registration_token',
                'registration_token_expires'
            ),
            'classes': ('wide',)
        }),
        (_('User Preferences'), {
            'fields': (
                'nickname',
                'language',
                'timezone',
                'avatar_url',
                'bio'
            )
        }),
    )

    @admin.display(description=_('Date Joined'))
    def user_date_joined(self, obj):
        """Display user's date joined"""
        return obj.user.date_joined

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return (super().get_queryset(request)
                .select_related('user'))
