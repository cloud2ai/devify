from __future__ import annotations

import logging
from dataclasses import dataclass

import stripe
from djstripe.models import Customer
from django.contrib.auth.models import User
from django.db.models import QuerySet

from billing.models import PlanPrice, Subscription, UserCredits
from billing.serializers import SubscriptionSerializer, UserCreditsSerializer
from billing.services.audit_service import queue_billing_audit_event
from billing.services.config_service import get_stripe_secret_key
from billing.services.customer_identity import resolve_customer_for_user
from billing.services.credits_service import CreditsService
from billing.services.subscription_service import SubscriptionService
from billing.services.stripe_compat import StripePlanMappingError, stripe_value

from .base import PaymentCheckProvider

logger = logging.getLogger(__name__)

SAFE_REMOTE_STATUSES = {
    'active',
    'trialing',
    'past_due',
    'incomplete',
    'unpaid',
}

TERMINAL_REMOTE_STATUSES = {
    'canceled',
    'incomplete_expired',
    'paused',
}


@dataclass(slots=True)
class StripeCheckOutcome:
    provider: str
    scanned_count: int = 0
    repaired_count: int = 0
    failed_count: int = 0
    manual_count: int = 0
    would_fix_count: int = 0
    in_sync_count: int = 0
    differences: list[dict] | None = None

    def as_dict(self) -> dict:
        differences = self.differences or []
        return {
            'provider': self.provider,
            'scanned_count': self.scanned_count,
            'repaired_count': self.repaired_count,
            'failed_count': self.failed_count,
            'manual_count': self.manual_count,
            'would_fix_count': self.would_fix_count,
            'in_sync_count': self.in_sync_count,
            'differences': differences,
        }


class StripePaymentCheckProvider(PaymentCheckProvider):
    name = 'stripe'
    _stripe_value = staticmethod(stripe_value)

    def is_configured(self) -> bool:
        return bool(get_stripe_secret_key())

    @staticmethod
    def _stripe_payload(obj) -> dict:
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return dict(getattr(obj, '__dict__', {}) or {})

    @classmethod
    def _remote_plan_slug(cls, remote_subscription) -> str | None:
        remote_data = cls._stripe_payload(remote_subscription)
        items = remote_data.get('items') or {}
        item_list = items.get('data') or []
        if not item_list:
            return None
        first_item = item_list[0] or {}
        price = first_item.get('price') or {}
        metadata = price.get('metadata') or {}
        if isinstance(metadata, dict):
            return metadata.get('devify_plan_slug')
        return cls._stripe_value(metadata, 'devify_plan_slug')

    @staticmethod
    def _period_value(subscription: Subscription | None, field: str):
        if not subscription:
            return None
        value = getattr(subscription, field, None)
        if value is None:
            return None
        if hasattr(value, 'timestamp'):
            return int(value.timestamp())
        return value

    @classmethod
    def _pick_remote_subscription(cls, subscriptions):
        if not subscriptions:
            return None

        for status in (
            'active',
            'trialing',
            'past_due',
            'incomplete',
            'unpaid',
        ):
            candidates = [
                sub
                for sub in subscriptions
                if cls._stripe_value(sub, 'status') == status
            ]
            if candidates:
                return max(
                    candidates,
                    key=lambda sub: cls._stripe_value(sub, 'created', 0) or 0,
                )

        for status in TERMINAL_REMOTE_STATUSES:
            candidates = [
                sub
                for sub in subscriptions
                if cls._stripe_value(sub, 'status') == status
            ]
            if candidates:
                return max(
                    candidates,
                    key=lambda sub: cls._stripe_value(sub, 'created', 0) or 0,
                )
        return None

    @staticmethod
    def _get_local_active_subscription(user: User) -> Subscription | None:
        return (
            Subscription.objects.select_related(
                'plan',
                'provider',
                'djstripe_subscription',
            )
            .filter(user=user, status='active')
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def _get_active_local_subscriptions(user: User) -> list[Subscription]:
        return list(
            Subscription.objects.select_related(
                'plan',
                'provider',
                'djstripe_subscription',
            )
            .filter(user=user, status='active')
            .order_by('-created_at')
        )

    def iter_targets(self):
        return Customer.objects.select_related('subscriber').filter(
            subscriber__isnull=False
        )

    def list_remote_subscriptions(self, customer: Customer):
        stripe.api_key = get_stripe_secret_key()
        remote_list = stripe.Subscription.list(
            customer=customer.id,
            status='all',
            limit=20,
        )
        return list(getattr(remote_list, 'data', []) or [])

    def build_local_match_key(self, local_subscription: Subscription | None):
        if not local_subscription:
            return None
        return {
            'provider': (
                local_subscription.provider.name
                if local_subscription.provider
                else ''
            ),
            'plan_slug': (
                local_subscription.plan.slug if local_subscription.plan else ''
            ),
            'djstripe_subscription_id': (
                local_subscription.djstripe_subscription.id
                if local_subscription.djstripe_subscription
                else None
            ),
        }

    @classmethod
    def compare_local_and_remote(
        cls,
        local_subscription: Subscription | None,
        remote_subscription,
    ) -> dict:
        remote_status = cls._stripe_value(remote_subscription, 'status')
        if (
            remote_status not in SAFE_REMOTE_STATUSES
            and remote_status not in TERMINAL_REMOTE_STATUSES
        ):
            remote_payload = cls._stripe_payload(remote_subscription)
            remote_items = remote_payload.get('items') or {}
            remote_item = (remote_items.get('data') or [{}])[0] or {}
            remote_price = remote_item.get('price') or {}
            remote_price_id = remote_price.get('id')
            remote_plan_slug = cls._remote_plan_slug(remote_subscription)
            if not remote_plan_slug and remote_price_id:
                plan_price = PlanPrice.objects.select_related('plan').filter(
                    provider__name='stripe',
                    provider_price_id=remote_price_id,
                ).first()
                if plan_price:
                    remote_plan_slug = plan_price.plan.slug
            return {
                'remote_plan_slug': remote_plan_slug,
                'remote_status': remote_status,
                'remote_period_start': remote_item.get('current_period_start'),
                'remote_period_end': remote_item.get('current_period_end'),
                'remote_cancel_at_period_end': remote_payload.get(
                    'cancel_at_period_end'
                ),
                'differences': ['remote_status_requires_manual_review'],
            }

        remote_plan_slug = cls._remote_plan_slug(remote_subscription)
        remote_payload = cls._stripe_payload(remote_subscription)
        remote_items = remote_payload.get('items') or {}
        remote_item = (remote_items.get('data') or [{}])[0] or {}
        if not remote_plan_slug:
            remote_price = remote_item.get('price') or {}
            remote_price_id = remote_price.get('id')
            if remote_price_id:
                plan_price = PlanPrice.objects.select_related('plan').filter(
                    provider__name='stripe',
                    provider_price_id=remote_price_id,
                ).first()
                if plan_price:
                    remote_plan_slug = plan_price.plan.slug
        remote_period_start = remote_item.get('current_period_start')
        remote_period_end = remote_item.get('current_period_end')
        remote_cancel_at_period_end = remote_payload.get('cancel_at_period_end')

        differences: list[str] = []
        if not local_subscription:
            differences.append('missing_local_subscription')
        else:
            # NOTE: Only compare Stripe-managed subscriptions here.
            # Platform subscriptions are intentionally excluded from this provider.
            local_provider_name = (
                local_subscription.provider.name
                if local_subscription.provider
                else None
            )
            local_plan_slug = (
                local_subscription.plan.slug if local_subscription.plan else None
            )
            if local_provider_name != cls.name:
                differences.append('provider_mismatch')
            if remote_plan_slug and local_plan_slug != remote_plan_slug:
                differences.append('plan_mismatch')
            if local_subscription.status != remote_status:
                differences.append('status_mismatch')
            if (
                cls._period_value(local_subscription, 'current_period_start')
                != remote_period_start
            ):
                differences.append('period_start_mismatch')
            if (
                cls._period_value(local_subscription, 'current_period_end')
                != remote_period_end
            ):
                differences.append('period_end_mismatch')
            # NOTE: Stripe's cancel_at_period_end is the inverse of our local auto_renew.
            # Do not compare these with "!="; matching states are:
            #   auto_renew=True  <-> cancel_at_period_end=False
            #   auto_renew=False <-> cancel_at_period_end=True
            if local_subscription.auto_renew == remote_cancel_at_period_end:
                differences.append('auto_renew_mismatch')

        return {
            'remote_plan_slug': remote_plan_slug,
            'remote_status': remote_status,
            'remote_period_start': remote_period_start,
            'remote_period_end': remote_period_end,
            'remote_cancel_at_period_end': remote_cancel_at_period_end,
            'differences': differences,
        }

    def repair_local_state(
        self,
        *,
        user: User,
        remote_subscription,
        actor_context: dict | None,
        mode: str,
    ) -> dict:
        remote_status = self._stripe_value(remote_subscription, 'status')
        before_subscription = self._get_local_active_subscription(user)
        before_credits = UserCredits.objects.filter(
            user=user,
            is_active=True,
        ).first()

        # NOTE: Use the same Stripe -> dj-stripe -> local sync entry point as
        # manual admin recovery so both flows stay behaviorally identical.
        try:
            subscription = SubscriptionService.sync_from_stripe_subscription(
                remote_subscription
            )
        except StripePlanMappingError as exc:
            return {
                'provider': self.name,
                'decision': 'manual',
                'reason': 'unresolved_remote_plan_mapping',
                'user_id': user.id,
                'username': user.username,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
                'remote_status': remote_status,
                'remote_plan_slug': self._remote_plan_slug(remote_subscription),
                'remote_price_id': exc.price_id,
                'local_subscription_id': (
                    before_subscription.id if before_subscription else None
                ),
                'local_status': (
                    before_subscription.status if before_subscription else None
                ),
                'differences': ['remote_plan_mapping_missing'],
            }
        credits = UserCredits.objects.filter(
            user=user,
            is_active=True,
        ).first()
        if remote_status == 'canceled':
            Subscription.objects.filter(
                user=user,
                status='active',
            ).exclude(id=subscription.id).update(
                status='canceled',
                auto_renew=False,
            )
        if credits:
            credits.subscription = subscription
            djstripe_customer = getattr(
                getattr(subscription, 'djstripe_subscription', None),
                'customer',
                None,
            )
            if djstripe_customer:
                credits.djstripe_customer = djstripe_customer
            credits.save()
        if subscription.status == 'active':
            CreditsService.reset_period_credits(user.id)

        actor_context = actor_context or {}
        queue_billing_audit_event(
            action_type='payment_check.repair',
            source=actor_context.get('source', 'system_task'),
            actor_id=actor_context.get('actor_id'),
            actor_name=actor_context.get('actor_name', ''),
            target_user_id=user.id,
            target_username=user.username,
            resource_type='subscription',
            resource_id=subscription.id,
            ip_address=actor_context.get('ip_address'),
            user_agent=actor_context.get('user_agent', ''),
            before_data={
                'subscription': (
                    SubscriptionSerializer(before_subscription).data
                    if before_subscription
                    else None
                ),
                'credits': (
                    UserCreditsSerializer(before_credits).data
                    if before_credits
                    else None
                ),
            },
            after_data={
                'subscription': SubscriptionSerializer(subscription).data,
                'credits': (
                    UserCreditsSerializer(credits).data if credits else None
                ),
            },
            context={
                'provider': self.name,
                'mode': mode,
                'remote_status': remote_status,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
            },
        )

        return {
            'provider': self.name,
            'decision': 'fixed',
            'reason': 'repaired_from_remote',
            'user_id': user.id,
            'username': user.username,
            'remote_subscription_id': self._stripe_value(
                remote_subscription, 'id'
            ),
            'remote_status': self._stripe_value(remote_subscription, 'status'),
            'local_subscription_id': subscription.id,
            'local_status': subscription.status,
        }

    def check_target(
        self,
        customer: Customer,
        *,
        mode: str = 'report_only',
        actor_context: dict | None = None,
    ) -> dict:
        user = customer.subscriber
        if user is None:
            return {
                'provider': self.name,
                'decision': 'skipped',
                'reason': 'customer_has_no_user',
                'customer_id': customer.id,
            }

        local_subscription = self._get_local_active_subscription(user)
        local_provider_name = (
            local_subscription.provider.name
            if local_subscription and local_subscription.provider
            else None
        )

        remote_subscription = self._pick_remote_subscription(
            self.list_remote_subscriptions(customer)
        )
        if not remote_subscription:
            if local_subscription and local_provider_name and local_provider_name != self.name:
                # NOTE: A non-Stripe local subscription is not a data mismatch.
                # It is an intentional platform-managed subscription, so skip it.
                return {
                    'provider': self.name,
                    'decision': 'skipped',
                    'reason': 'platform_subscription',
                    'user_id': user.id,
                    'username': user.username,
                    'local_subscription_id': local_subscription.id,
                    'local_status': local_subscription.status,
                    'local_provider': local_provider_name,
                }
            if local_subscription and local_subscription.status == 'active':
                # NOTE: If Stripe has no active subscription but local still does,
                # we need manual review because this may be a stale local record
                # or a cancellation that has not been reflected yet.
                return {
                    'provider': self.name,
                    'decision': 'manual',
                    'reason': 'local_has_subscription_but_remote_missing',
                    'user_id': user.id,
                    'username': user.username,
                    'local_subscription_id': local_subscription.id,
                    'local_status': local_subscription.status,
                }
            return {
                'provider': self.name,
                'decision': 'in_sync',
                'reason': 'no_remote_subscription',
                'user_id': user.id,
                'username': user.username,
                'local_subscription_id': (
                    local_subscription.id if local_subscription else None
                ),
                'local_status': (
                    local_subscription.status if local_subscription else None
                ),
            }

        diff = self.compare_local_and_remote(local_subscription, remote_subscription)
        remote_status = diff['remote_status']
        remote_plan_slug = diff['remote_plan_slug']
        differences = diff['differences']

        if remote_status == 'canceled':
            if local_subscription and local_subscription.status == 'active':
                if mode == 'auto_fix_safe':
                    repaired = self.repair_local_state(
                        user=user,
                        remote_subscription=remote_subscription,
                        actor_context=actor_context,
                        mode=mode,
                    )
                    if repaired.get('decision') == 'fixed':
                        repaired['reason'] = 'remote_subscription_canceled'
                        repaired['differences'] = differences
                    return repaired

                return {
                    'provider': self.name,
                    'decision': 'would_fix',
                    'reason': 'remote_subscription_canceled',
                    'user_id': user.id,
                    'username': user.username,
                    'remote_subscription_id': self._stripe_value(
                        remote_subscription, 'id'
                    ),
                    'remote_status': remote_status,
                    'remote_plan_slug': remote_plan_slug,
                    'local_subscription_id': local_subscription.id,
                    'local_status': local_subscription.status,
                    'differences': differences,
                }

            return {
                'provider': self.name,
                'decision': 'in_sync',
                'reason': 'remote_subscription_canceled',
                'user_id': user.id,
                'username': user.username,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
                'remote_status': remote_status,
                'remote_plan_slug': remote_plan_slug,
                'local_subscription_id': (
                    local_subscription.id if local_subscription else None
                ),
                'local_status': (
                    local_subscription.status if local_subscription else None
                ),
                'differences': [],
            }

        if remote_status in {'incomplete_expired', 'paused'}:
            return {
                'provider': self.name,
                'decision': 'manual',
                'reason': 'remote_terminal_status',
                'user_id': user.id,
                'username': user.username,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
                'remote_status': remote_status,
                'remote_plan_slug': remote_plan_slug,
                'local_subscription_id': (
                    local_subscription.id if local_subscription else None
                ),
                'local_status': (
                    local_subscription.status if local_subscription else None
                ),
                'differences': differences,
            }

        if remote_status not in SAFE_REMOTE_STATUSES:
            return {
                'provider': self.name,
                'decision': 'manual',
                'reason': 'remote_status_requires_manual_review',
                'user_id': user.id,
                'username': user.username,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
                'remote_status': remote_status,
                'remote_plan_slug': remote_plan_slug,
                'local_subscription_id': (
                    local_subscription.id if local_subscription else None
                ),
                'local_status': (
                    local_subscription.status if local_subscription else None
                ),
                'differences': differences,
            }

        if not remote_plan_slug and local_subscription:
            local_plan_slug = local_subscription.plan.slug if local_subscription.plan else None
            if local_plan_slug and local_plan_slug != 'free':
                return {
                    'provider': self.name,
                    'decision': 'manual',
                    'reason': 'ambiguous_remote_plan_missing',
                    'user_id': user.id,
                    'username': user.username,
                    'remote_subscription_id': self._stripe_value(
                        remote_subscription, 'id'
                    ),
                    'remote_status': remote_status,
                    'remote_plan_slug': remote_plan_slug,
                    'local_subscription_id': local_subscription.id,
                    'local_plan_slug': local_plan_slug,
                    'differences': differences,
                }

        if not local_subscription or differences:
            if mode == 'auto_fix_safe':
                repaired = self.repair_local_state(
                    user=user,
                    remote_subscription=remote_subscription,
                    actor_context=actor_context,
                    mode=mode,
                )
                if repaired.get('decision') == 'fixed':
                    repaired['reason'] = (
                        'missing_local_subscription'
                        if not local_subscription
                        else 'stale_local_subscription'
                    )
                    repaired['differences'] = differences
                return repaired

            return {
                'provider': self.name,
                'decision': 'would_fix',
                'reason': (
                    'missing_local_subscription'
                    if not local_subscription
                    else 'stale_local_subscription'
                ),
                'user_id': user.id,
                'username': user.username,
                'remote_subscription_id': self._stripe_value(
                    remote_subscription, 'id'
                ),
                'remote_status': remote_status,
                'remote_plan_slug': remote_plan_slug,
                'local_subscription_id': (
                    local_subscription.id if local_subscription else None
                ),
                'local_status': (
                    local_subscription.status if local_subscription else None
                ),
                'differences': differences,
            }

        return {
            'provider': self.name,
            'decision': 'in_sync',
            'reason': 'already_in_sync',
            'user_id': user.id,
            'username': user.username,
            'remote_subscription_id': self._stripe_value(
                remote_subscription, 'id'
            ),
            'remote_status': remote_status,
            'remote_plan_slug': remote_plan_slug,
            'local_subscription_id': local_subscription.id if local_subscription else None,
            'local_status': local_subscription.status if local_subscription else None,
            'differences': [],
        }

    def check_user(
        self,
        user: User,
        *,
        mode: str = 'report_only',
        actor_context: dict | None = None,
    ) -> dict:
        customer = self._get_customer_for_user(user)
        if not customer:
            return {
                'provider': self.name,
                'decision': 'skipped',
                'reason': 'no_customer',
                'user_id': user.id,
                'username': user.username,
            }
        return self.check_target(
            customer,
            mode=mode,
            actor_context=actor_context,
        )

    def _get_customer_for_user(self, user: User) -> Customer | None:
        return resolve_customer_for_user(user)

    def run(
        self,
        *,
        mode: str = 'report_only',
        actor_context: dict | None = None,
    ) -> dict:
        if mode not in {'report_only', 'auto_fix_safe'}:
            raise ValueError(f'Unsupported payment check mode: {mode}')

        if not self.is_configured():
            return {
                'provider': self.name,
                'status': 'skipped',
                'reason': 'Stripe secret key is not configured',
                'scanned_count': 0,
                'repaired_count': 0,
                'failed_count': 0,
                'manual_count': 0,
                'would_fix_count': 0,
                'in_sync_count': 0,
                'differences': [],
            }

        stripe.api_key = get_stripe_secret_key()
        outcome = StripeCheckOutcome(provider=self.name, differences=[])
        customers: QuerySet[Customer] = self.iter_targets()
        for customer in customers:
            try:
                result = self.check_target(
                    customer,
                    mode=mode,
                    actor_context=actor_context,
                )
                outcome.differences.append(result)
                decision = result.get('decision')
                if decision != 'skipped':
                    outcome.scanned_count += 1
                if decision == 'fixed':
                    outcome.repaired_count += 1
                elif decision == 'manual':
                    outcome.manual_count += 1
                elif decision == 'would_fix':
                    outcome.would_fix_count += 1
                elif decision == 'in_sync':
                    outcome.in_sync_count += 1
            except Exception as exc:
                logger.exception(
                    'Stripe payment check failed for user_id=%s customer_id=%s: %s',
                    getattr(customer, 'subscriber_id', None),
                    customer.id,
                    exc,
                )
                outcome.failed_count += 1
                outcome.differences.append(
                    {
                        'provider': self.name,
                        'decision': 'error',
                        'user_id': customer.subscriber_id,
                        'username': (
                            customer.subscriber.username
                            if customer.subscriber
                            else ''
                        ),
                        'error': str(exc),
                    }
                )

        return outcome.as_dict()
