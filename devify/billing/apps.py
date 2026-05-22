from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        """
        Import webhook handlers to register signals, and inject
        Stripe API keys into Django settings for dj-stripe.
        """
        import billing.webhooks
        _inject_stripe_settings()


def _inject_stripe_settings():
    """Read Stripe keys from BillingConfig and set them in Django settings.

    dj-stripe reads STRIPE_TEST_SECRET_KEY, STRIPE_LIVE_SECRET_KEY, etc.
    from Django settings. Since our keys live in the BillingConfig database
    model, we must copy them into settings during app startup so dj-stripe
    can find them.
    """
    from django.conf import settings
    from django.db.utils import OperationalError, ProgrammingError

    try:
        from billing.services.config_service import (
            get_stripe_secret_key,
            get_stripe_publishable_key,
            get_stripe_webhook_secret,
        )

        secret_key = get_stripe_secret_key()
        if secret_key:
            settings.STRIPE_TEST_SECRET_KEY = secret_key
            settings.STRIPE_LIVE_SECRET_KEY = secret_key

        publishable_key = get_stripe_publishable_key()
        if publishable_key:
            settings.STRIPE_PUBLISHABLE_KEY = publishable_key

        webhook_secret = get_stripe_webhook_secret()
        if webhook_secret:
            settings.DJSTRIPE_WEBHOOK_SECRET = webhook_secret

    except (OperationalError, ProgrammingError):
        # Database not ready yet (e.g., during migrations)
        pass
