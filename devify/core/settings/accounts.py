"""
Accounts and Authentication Configuration

This module contains all settings related to:
- User registration and authentication
- Email configuration for registration emails
- Google OAuth configuration
- Virtual email system
"""

import os


# ============================
# Email Configuration
# ============================

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')

EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))

EMAIL_USE_TLS = (
    os.getenv('EMAIL_USE_TLS', 'True').lower()
    in ('true', '1', 'yes', 'on')
)

EMAIL_USE_SSL = (
    os.getenv('EMAIL_USE_SSL', 'False').lower()
    in ('true', '1', 'yes', 'on')
)

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')

EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'noreply@devify.local'
)


# ============================
# Social Account Providers Configuration
# ============================

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    },
}

# Custom adapter for business logic (user creation, profile setup)
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'

# Basic account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_LOGIN_ON_GET = True

# Account configuration
# Unique email addresses (prevent duplicate registrations)
ACCOUNT_UNIQUE_EMAIL = True

# Email-based authentication for social accounts
# If OAuth email matches existing user, auto-connect instead of creating new user
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# ============================
# OAuth Redirect Configuration
# ============================

# Frontend URL
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Keep OAuth endpoints active (HEADLESS_ONLY=False)
# OAuth flows require traditional /accounts/ endpoints for provider callbacks
HEADLESS_ONLY = False

# OAuth callback redirect URL
# Points to custom view that generates JWT tokens before redirecting to frontend
LOGIN_REDIRECT_URL = "/accounts/oauth/callback/"

# Frontend URLs for email verification and password reset (optional)
# Note: socialaccount_signup is NOT used as we have custom redirect logic
HEADLESS_FRONTEND_URLS = {
    "socialaccount_login_error": f"{FRONTEND_URL}/auth/oauth/error",
    "account_confirm_email": f"{FRONTEND_URL}/account/verify-email/{{key}}",
    "account_reset_password": f"{FRONTEND_URL}/account/password/reset",
    "account_reset_password_from_key": (
        f"{FRONTEND_URL}/account/password/reset/key/{{key}}"
    ),
}


# ============================
# Registration Configuration
# ============================

REGISTRATION_TOKEN_EXPIRY_HOURS = int(
    os.getenv('REGISTRATION_TOKEN_EXPIRY_HOURS', '24')
)
