"""
Context processors for exposing frontend related configuration to templates.
"""

from django.conf import settings


def frontend_settings(_request):
    """
    Provide frontend URL and support contact for template rendering.
    """
    return {
        "frontend_url": getattr(settings, "FRONTEND_URL", "/"),
        "support_email": getattr(
            settings,
            "SUPPORT_EMAIL",
            "support@devify.local",
        ),
    }
