from __future__ import annotations

from django.db import transaction
from djstripe.models import Account, APIKey
from djstripe.settings import djstripe_settings

from billing.services.stripe_compat import stripe_to_dict


@transaction.atomic
def ensure_djstripe_owner_account(api_key: str):
    """
    Ensure dj-stripe has a persisted Account linked to the provided API key.

    Use dj-stripe's own syncing helper so the account row is created from the
    official Stripe payload and the API key is linked to that account.
    """
    api_key = (api_key or '').strip()
    if not api_key:
        raise ValueError('Stripe secret key is not configured')

    api_key_record, _ = APIKey.objects.get_or_create_by_api_key(api_key)
    if api_key_record.djstripe_owner_account_id:
        return api_key_record.djstripe_owner_account

    account_data = Account.stripe_class.retrieve(
        api_key=api_key,
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
    )
    account = Account.sync_from_stripe_data(
        stripe_to_dict(account_data),
        api_key=api_key,
    )
    api_key_record.djstripe_owner_account = account
    api_key_record.save(update_fields=['djstripe_owner_account'])
    return account
