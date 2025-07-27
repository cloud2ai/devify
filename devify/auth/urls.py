from django.urls import path
from dj_rest_auth.views import (
    LoginView, LogoutView, UserDetailsView,
    PasswordResetView, PasswordResetConfirmView, PasswordChangeView,
)
from dj_rest_auth.registration.views import (
    RegisterView, VerifyEmailView,
    SocialLoginView, SocialConnectView
)

urlpatterns = [
    # Login endpoint
    path(
        'api/v1/auth/login',
        LoginView.as_view(),
        name='rest_login'
    ),
    # Logout endpoint
    path(
        'api/v1/auth/logout',
        LogoutView.as_view(),
        name='rest_logout'
    ),
    # Get or update user details
    path(
        'api/v1/auth/user',
        UserDetailsView.as_view(),
        name='rest_user_details'
    ),
    # Request password reset
    path(
        'api/v1/auth/password/reset',
        PasswordResetView.as_view(),
        name='rest_password_reset'
    ),
    # Confirm password reset
    path(
        'api/v1/auth/password/reset/confirm',
        PasswordResetConfirmView.as_view(),
        name='rest_password_reset_confirm'
    ),
    # Change password
    path(
        'api/v1/auth/password/change',
        PasswordChangeView.as_view(),
        name='rest_password_change'
    ),
    # Register new user
    path(
        'api/v1/auth/registration',
        RegisterView.as_view(),
        name='rest_register'
    ),
    # Verify email after registration
    path(
        'api/v1/auth/registration/verify-email',
        VerifyEmailView.as_view(),
        name='rest_verify_email'
    ),
    # Social login endpoint
    path(
        'api/v1/auth/social/login',
        SocialLoginView.as_view(),
        name='social_login'
    ),
    # Social connect endpoint
    path(
        'api/v1/auth/social/connect',
        SocialConnectView.as_view(),
        name='social_connect'
    ),
    # Social disconnect endpoint (uncomment if needed)
    # path(
    #     'api/v1/auth/social/disconnect',
    #     SocialDisconnectView.as_view(),
    #     name='social_disconnect'
    # ),
]