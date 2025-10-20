"""
Accounts views package.

This package contains all authentication and user management views,
organized by functionality for better maintainability.
"""

# Import all views for backward compatibility
from .registration import (
    SendRegistrationEmailView,
    VerifyRegistrationTokenView,
    CompleteRegistrationView,
    CheckVirtualEmailUsernameView,
)

from .oauth import (
    CompleteGoogleSetupView,
    OAuthCallbackRedirectView,
)

from .password import (
    SendPasswordResetEmailView,
    ConfirmPasswordResetView,
)

from .user import (
    CustomUserDetailsView,
)

from .scenes import (
    GetAvailableScenesView,
)

__all__ = [
    # Registration views
    'SendRegistrationEmailView',
    'VerifyRegistrationTokenView',
    'CompleteRegistrationView',
    'CheckVirtualEmailUsernameView',

    # OAuth views
    'CompleteGoogleSetupView',
    'OAuthCallbackRedirectView',

    # Password views
    'SendPasswordResetEmailView',
    'ConfirmPasswordResetView',

    # User views
    'CustomUserDetailsView',

    # Scene views
    'GetAvailableScenesView',
]
