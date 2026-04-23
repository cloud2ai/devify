"""
Token-related auth views.

Handles JWT token refresh for the frontend refresh flow.
"""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView


@method_decorator(csrf_exempt, name='dispatch')
class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh a JWT access token using a valid refresh token.

    The frontend stores the refresh token and posts it here when an access
    token expires.
    """

    permission_classes = [AllowAny]
