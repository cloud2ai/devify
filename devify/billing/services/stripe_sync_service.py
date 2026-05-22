from __future__ import annotations

import stripe

from billing.models import Plan, PlanPrice
from billing.services.config_service import get_stripe_secret_key
from billing.services.subscription_service import SubscriptionService


class StripePlanSyncService:
    """
    Sync a local plan to Stripe product/price records.

    This service intentionally handles only the Stripe provider. It is used by
    both the manual repair command and the admin console sync action.
    """

    provider_name = 'stripe'
    currency = 'USD'
    interval = 'month'
    unified_product_name = 'aimychats.com Subscription'
    unified_product_description = 'Devify subscription plans for aimychats.com'

    @classmethod
    def sync_plan(cls, plan: Plan) -> dict[str, object]:
        if not plan:
            raise ValueError('Plan is required')
        if plan.status != Plan.STATUS_ACTIVE:
            raise ValueError('Only active plans can be synced to Stripe')
        if plan.is_internal:
            raise ValueError('Internal plans cannot be synced to Stripe')
        if not plan.allow_self_purchase:
            raise ValueError('Plan must allow self-purchase before syncing')

        secret_key = get_stripe_secret_key()
        if not secret_key:
            raise ValueError('Stripe secret key is not configured')

        stripe.api_key = secret_key
        stripe_provider = SubscriptionService.get_or_create_payment_provider(
            cls.provider_name
        )
        product_id = cls._ensure_unified_product()
        price_result = cls._ensure_price(plan, product_id)

        plan_price, _ = PlanPrice.objects.update_or_create(
            plan=plan,
            provider=stripe_provider,
            interval=cls.interval,
            defaults={
                'provider_product_id': product_id,
                'provider_price_id': price_result['price_id'],
                'currency': cls.currency,
                'unit_amount_cents': plan.monthly_price_cents,
                'is_active': True,
            },
        )

        return {
            'provider_name': stripe_provider.name,
            'plan_price_id': plan_price.id,
            'provider_product_id': product_id,
            'provider_price_id': price_result['price_id'],
            'created_new_price': price_result['created_new_price'],
            'deactivated_price_id': price_result['deactivated_price_id'],
        }

    @classmethod
    def sync_active_plans(cls) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        plans = Plan.objects.filter(
            status=Plan.STATUS_ACTIVE,
            is_internal=False,
            allow_self_purchase=True,
        ).order_by('monthly_price_cents', 'id')
        for plan in plans:
            result = cls.sync_plan(plan)
            result['plan_id'] = plan.id
            result['plan_slug'] = plan.slug
            results.append(result)
        return results

    @classmethod
    def _ensure_unified_product(cls) -> str:
        search_query = (
            'metadata["devify_managed"]:"true" AND '
            'metadata["devify_unified"]:"true"'
        )
        search_results = stripe.Product.search(query=search_query)

        if search_results.data:
            return search_results.data[0].id

        product = stripe.Product.create(
            name=cls.unified_product_name,
            description=cls.unified_product_description,
            metadata={
                'devify_managed': 'true',
                'devify_unified': 'true',
            },
        )
        return product.id

    @classmethod
    def _ensure_price(
        cls,
        plan: Plan,
        product_id: str,
    ) -> dict[str, object]:
        prices = stripe.Price.list(
            product=product_id,
            active=True,
            limit=100,
        )
        matching_price = cls._find_matching_price(prices.data, plan.slug)
        if matching_price and matching_price.unit_amount == plan.monthly_price_cents:
            return {
                'price_id': matching_price.id,
                'created_new_price': False,
                'deactivated_price_id': None,
            }

        deactivated_price_id = None
        if matching_price and matching_price.unit_amount != plan.monthly_price_cents:
            stripe.Price.modify(matching_price.id, active=False)
            deactivated_price_id = matching_price.id

        price = stripe.Price.create(
            product=product_id,
            unit_amount=plan.monthly_price_cents,
            currency=cls.currency.lower(),
            recurring={'interval': cls.interval},
            metadata={
                'devify_plan_slug': plan.slug,
                'devify_managed': 'true',
            },
        )
        return {
            'price_id': price.id,
            'created_new_price': True,
            'deactivated_price_id': deactivated_price_id,
        }

    @staticmethod
    def _find_matching_price(prices, plan_slug):
        for price in prices:
            metadata = getattr(price, 'metadata', None)
            if metadata is None:
                continue

            if isinstance(metadata, dict):
                slug = metadata.get('devify_plan_slug')
            else:
                slug = getattr(metadata, 'devify_plan_slug', None)
                if slug is None:
                    try:
                        slug = metadata['devify_plan_slug']
                    except (KeyError, TypeError, AttributeError):
                        slug = None

            if slug == plan_slug:
                return price
        return None
