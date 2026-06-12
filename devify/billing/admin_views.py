from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch, Q, Sum
from django.core.paginator import Paginator
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import (
    BillingAuditLog,
    CreditsTransaction,
    PaymentRecord,
    Plan,
    PlanPrice,
    Subscription,
    UserCredits,
)
from billing.serializers import (
    BillingAuditLogSerializer,
    CreditsTransactionSerializer,
    PaymentRecordSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    UserCreditsSerializer,
)
from billing.services.audit_service import (
    get_request_ip,
    get_request_user_agent,
    queue_billing_audit_event,
)
from billing.services.payment_check.service import PaymentCheckService
from billing.services.payment_check_scheduler import (
    sync_payment_check_periodic_task,
)
from billing.services.payment_record_backfill_scheduler import (
    sync_payment_record_backfill_periodic_task,
)
from billing.services.payment_record_service import backfill_payment_records
from billing.services.customer_identity import (
    summarize_customer_identity_for_user,
)
from billing.services.stripe_sync_service import StripePlanSyncService
from billing.services.config_service import (
    get_billing_config,
    get_public_billing_status,
    serialize_billing_config,
    update_billing_config,
)
from billing.services.credits_service import CreditsService
from billing.services.subscription_service import SubscriptionService

User = get_user_model()
logger = logging.getLogger(__name__)


class BillingConfigUpdateSerializer(serializers.Serializer):
    stripe_live_mode = serializers.BooleanField(required=False)
    stripe_publishable_key = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    stripe_live_secret_key = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    stripe_test_secret_key = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    stripe_webhook_secret = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    payment_callback_url = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    payment_check_enabled = serializers.BooleanField(required=False)
    payment_check_providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    payment_check_schedule = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    payment_record_backfill_enabled = serializers.BooleanField(
        required=False
    )
    payment_record_backfill_schedule = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    payment_record_backfill_lookback_days = serializers.IntegerField(
        required=False,
        min_value=1,
    )
    payment_record_backfill_providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    default_free_credits = serializers.IntegerField(required=False, min_value=0)
    workflow_cost_credits = serializers.IntegerField(required=False, min_value=1)
    auto_refund_system_errors = serializers.BooleanField(required=False)
    self_purchase_enabled = serializers.BooleanField(required=False)
    enabled_providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )

    def validate_payment_check_schedule(self, value):
        schedule = str(value or '').strip()
        if not schedule:
            return ''
        if len(schedule.split()) != 5:
            raise serializers.ValidationError(
                'Payment check schedule must be a 5-field cron expression.'
            )
        return schedule

    def validate_payment_record_backfill_schedule(self, value):
        schedule = str(value or '').strip()
        if not schedule:
            return ''
        if len(schedule.split()) != 5:
            raise serializers.ValidationError(
                'Successful invoice backfill schedule must be a 5-field cron expression.'
            )
        return schedule


class BillingPlanUpsertSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    slug = serializers.SlugField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    monthly_price_cents = serializers.IntegerField(required=False, min_value=0)
    metadata = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
    )
    status = serializers.ChoiceField(
        choices=Plan.STATUS_CHOICES,
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    is_internal = serializers.BooleanField(required=False)
    allow_self_purchase = serializers.BooleanField(required=False)


class BillingGrantCreditsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1, required=False)
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


class BillingAssignPlanSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(min_value=1, required=False)
    plan_slug = serializers.SlugField(required=False)

    def validate(self, attrs):
        if not attrs.get('plan_id') and not attrs.get('plan_slug'):
            raise serializers.ValidationError(
                {'plan_id': 'Either plan_id or plan_slug is required.'}
            )
        return attrs


class BillingBatchGrantCreditsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,
    )
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


def _paginate(queryset, request, default_page_size: int = 20):
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = max(
            1,
            min(100, int(request.query_params.get('page_size', default_page_size))),
        )
    except (TypeError, ValueError):
        page_size = default_page_size

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return paginator, page_obj


def _plan_with_stripe_data(plan: Plan) -> dict:
    plan_data = PlanSerializer(plan).data
    prefetched_prices = getattr(plan, 'stripe_plan_prices', None)
    if prefetched_prices is not None:
        stripe_price = prefetched_prices[0] if prefetched_prices else None
    else:
        stripe_price = PlanPrice.objects.filter(
            plan_id=plan.id,
            provider__name='stripe',
            is_active=True,
        ).first()
    plan_data['stripe_price_id'] = (
        stripe_price.provider_price_id if stripe_price else None
    )
    plan_data['stripe_product_id'] = (
        stripe_price.provider_product_id if stripe_price else None
    )
    return plan_data


def _assign_plan_for_user(
    user: User,
    plan: Plan,
    audit_context: dict | None = None,
) -> dict:
    existing_subscription = Subscription.objects.filter(
        user=user,
        status__in=['active', 'past_due', 'trialing'],
    ).select_related('plan', 'provider').order_by('-created_at').first()
    existing_credits = (
        UserCredits.objects.filter(
            user=user,
            is_active=True,
        )
        .select_related('subscription__plan')
        .first()
    )
    if existing_subscription and existing_subscription.provider:
        if existing_subscription.provider.name == 'stripe':
            raise serializers.ValidationError(
                {
                    'user_id': (
                        'Stripe subscriptions cannot be modified from the '
                        'admin console. Please cancel or transfer the '
                        'subscription first.'
                    )
                }
            )

    subscription = SubscriptionService.switch_plan_for_user(user, plan)
    credits = CreditsService.get_user_credits(user.id)
    created = existing_subscription is None
    replaced = (
        existing_subscription is not None
        and existing_subscription.plan_id != plan.id
    )
    if audit_context is not None:
        queue_billing_audit_event(
            action_type='subscription.assign',
            source=audit_context.get('source', 'admin_api'),
            actor_id=audit_context.get('actor_id'),
            actor_name=audit_context.get('actor_name', ''),
            target_user_id=user.id,
            target_username=user.username,
            resource_type='subscription',
            resource_id=subscription.id,
            ip_address=audit_context.get('ip_address'),
            user_agent=audit_context.get('user_agent', ''),
            before_data={
                'subscription': _subscription_audit_snapshot(
                    existing_subscription
                ),
                'credits': _credits_audit_snapshot(existing_credits),
            },
            after_data={
                'subscription': _subscription_audit_snapshot(subscription),
                'credits': _credits_audit_snapshot(credits),
            },
            context={
                'plan_id': plan.id,
                'plan_slug': plan.slug,
                'created': created,
                'replaced': replaced,
            },
        )

    return {
        'created': created,
        'replaced': replaced,
        'subscription': SubscriptionSerializer(subscription).data,
        'credits': UserCreditsSerializer(credits).data,
        'status_code': (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        ),
    }


def _request_audit_context(request) -> dict:
    return {
        'ip_address': get_request_ip(request),
        'user_agent': get_request_user_agent(request),
    }


def _plan_audit_snapshot(plan: Plan | None) -> dict | None:
    if not plan:
        return None
    return _plan_with_stripe_data(plan)


def _credits_audit_snapshot(credits: UserCredits | None) -> dict | None:
    if not credits:
        return None
    return UserCreditsSerializer(credits).data


def _subscription_audit_snapshot(subscription: Subscription | None) -> dict | None:
    if not subscription:
        return None
    return SubscriptionSerializer(subscription).data


class BillingAdminConfigAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(serialize_billing_config())

    def put(self, request):
        serializer = BillingConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before_config = serialize_billing_config()
        config = update_billing_config(
            get_billing_config(),
            serializer.validated_data,
        )
        after_config = serialize_billing_config(config)
        # Refresh in-memory Django settings so the new Stripe keys and webhook
        # secret take effect immediately without a server restart.
        from billing.apps import _inject_stripe_settings
        _inject_stripe_settings()
        sync_payment_check_periodic_task(config)
        sync_payment_record_backfill_periodic_task(config)
        queue_billing_audit_event(
            action_type='billing_config.update',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='billing_config',
            resource_id=config.id,
            ip_address=_request_audit_context(request)['ip_address'],
            user_agent=_request_audit_context(request)['user_agent'],
            before_data=before_config,
            after_data=after_config,
            context={
                'updated_fields': list(serializer.validated_data.keys()),
            },
        )
        return Response(after_config)


class BillingPaymentCheckRunSerializer(serializers.Serializer):
    providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    mode = serializers.ChoiceField(
        choices=('report_only', 'auto_fix_safe'),
        required=False,
        default='report_only',
    )


class BillingPaymentRecordBackfillRunSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, min_value=1)
    lookback_days = serializers.IntegerField(required=False, min_value=1)
    providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )


class BillingAdminOverviewAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        aggregates = UserCredits.objects.aggregate(
            total_base=Sum('base_credits'),
            total_bonus=Sum('bonus_credits'),
            total_consumed=Sum('consumed_credits'),
        )
        payment_aggregates = PaymentRecord.objects.aggregate(
            total_amount=Sum('amount_cents'),
        )
        config = get_public_billing_status()
        return Response(
            {
                'users_count': User.objects.count(),
                'active_credits_count': UserCredits.objects.filter(
                    is_active=True
                ).count(),
                'subscriptions_count': Subscription.objects.count(),
                'active_subscriptions_count': Subscription.objects.filter(
                    status='active'
                ).count(),
                'transactions_count': CreditsTransaction.objects.count(),
                'payments_count': PaymentRecord.objects.count(),
                'total_base_credits': aggregates['total_base'] or 0,
                'total_bonus_credits': aggregates['total_bonus'] or 0,
                'total_consumed_credits': aggregates['total_consumed'] or 0,
                'total_available_credits': (
                    (aggregates['total_base'] or 0)
                    + (aggregates['total_bonus'] or 0)
                    - (aggregates['total_consumed'] or 0)
                ),
                'total_payment_amount_cents': (
                    payment_aggregates['total_amount'] or 0
                ),
                'billing_status': config,
            }
        )


class BillingAdminUsersAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = User.objects.prefetch_related(
            Prefetch(
                'credits',
                queryset=UserCredits.objects.select_related(
                    'subscription__plan',
                ).order_by('-updated_at'),
                to_attr='billing_credits',
            ),
            Prefetch(
                'subscriptions',
                queryset=Subscription.objects.select_related(
                    'plan',
                    'provider',
                ).order_by('-updated_at'),
                to_attr='billing_subscriptions',
            ),
        ).order_by('-date_joined')

        search = (request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
            )

        paginator, page_obj = _paginate(queryset, request)
        results = []
        for user in page_obj.object_list:
            credits_list = getattr(user, 'billing_credits', [])
            subscriptions_list = getattr(user, 'billing_subscriptions', [])
            credits = next(
                (item for item in credits_list if item.is_active),
                credits_list[0] if credits_list else None,
            )
            active_subscription = next(
                (
                    item
                    for item in subscriptions_list
                    if item.status == 'active'
                ),
                None,
            )
            subscription = (
                credits.subscription
                if credits
                and credits.subscription
                and credits.subscription.status == 'active'
                else active_subscription
            )
            results.append(
                {
                    'id': user.id,
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'available_credits': (
                        credits.available_credits if credits else 0
                    ),
                    'base_credits': credits.base_credits if credits else 0,
                    'bonus_credits': credits.bonus_credits if credits else 0,
                    'consumed_credits': (
                        credits.consumed_credits if credits else 0
                    ),
                    'period_start': (
                        credits.period_start
                        if credits
                        else (
                            subscription.current_period_start
                            if subscription
                            else None
                        )
                    ),
                    'period_end': (
                        credits.period_end
                        if credits
                        else (
                            subscription.current_period_end
                            if subscription
                            else None
                        )
                    ),
                    'is_active': (
                        credits.is_active
                        if credits and subscription
                        else False
                    ),
                    'plan_name': (
                        subscription.plan.name
                        if subscription and subscription.plan
                        else None
                    ),
                    'provider_name': (
                        subscription.provider.display_name
                        if subscription and subscription.provider
                        else None
                    ),
                    'provider_key': (
                        subscription.provider.name
                        if subscription and subscription.provider
                        else None
                    ),
                    'subscription_status': (
                        subscription.status if subscription else None
                    ),
                    'plan_id': (
                        subscription.plan.id
                        if subscription and subscription.plan
                        else None
                    ),
                    'plan_slug': (
                        subscription.plan.slug
                        if subscription and subscription.plan
                        else None
                    ),
                    'updated_at': (
                        credits.updated_at if credits else user.date_joined
                    ),
                }
            )

        return Response(
            {
                'count': paginator.count,
                'results': results,
            }
        )

    def post(self, request, user_id=None):
        serializer = BillingGrantCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = user_id or serializer.validated_data.get('user_id')
        if not target_user_id:
            raise serializers.ValidationError(
                {'user_id': 'This field is required.'}
            )
        target_user = get_object_or_404(User, pk=target_user_id)
        before_credits = (
            UserCredits.objects.filter(
                user=target_user,
                is_active=True,
            )
            .select_related('subscription__plan')
            .first()
        )
        transaction = CreditsService.grant_bonus_credits(
            user_id=target_user_id,
            amount=serializer.validated_data['amount'],
            reason=serializer.validated_data['reason'],
            operator_id=request.user.id,
        )
        credits = CreditsService.get_user_credits(
            target_user_id
        )
        request_audit = _request_audit_context(request)
        queue_billing_audit_event(
            action_type='credits.grant',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            target_user_id=target_user.id,
            target_username=target_user.username,
            resource_type='credits_transaction',
            resource_id=transaction.id,
            ip_address=request_audit['ip_address'],
            user_agent=request_audit['user_agent'],
            before_data=_credits_audit_snapshot(before_credits),
            after_data=_credits_audit_snapshot(credits),
            context={
                'amount': serializer.validated_data['amount'],
                'reason': serializer.validated_data['reason'],
            },
        )
        return Response(
            {
                'transaction': CreditsTransactionSerializer(transaction).data,
                'credits': UserCreditsSerializer(credits).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BillingAdminIdentityConflictsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        results = []
        for user in User.objects.order_by('-date_joined').iterator(
            chunk_size=500
        ):
            identity_summary = summarize_customer_identity_for_user(user)
            if not identity_summary['has_conflict']:
                continue
            results.append(
                {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'match_count': identity_summary['match_count'],
                    'customers': identity_summary['customers'],
                }
            )

        return Response(
            {
                'count': len(results),
                'results': results,
            }
        )


class BillingAdminUserAssignPlanAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, user_id):
        serializer = BillingAssignPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, pk=user_id)
        request_audit = _request_audit_context(request)
        data = serializer.validated_data
        if data.get('plan_id'):
            plan = get_object_or_404(Plan, pk=data['plan_id'])
        else:
            plan = get_object_or_404(Plan, slug=data['plan_slug'])
        payload = _assign_plan_for_user(
            user,
            plan,
            audit_context={
                'source': 'admin_api',
                'actor_id': request.user.id,
                'actor_name': request.user.username,
                'ip_address': request_audit['ip_address'],
                'user_agent': request_audit['user_agent'],
            },
        )
        status_code = payload.pop('status_code')
        return Response(payload, status=status_code)


class BillingAdminUserAssignFreePlanAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        plan = get_object_or_404(Plan, slug='free')
        request_audit = _request_audit_context(request)
        payload = _assign_plan_for_user(
            user,
            plan,
            audit_context={
                'source': 'admin_api',
                'actor_id': request.user.id,
                'actor_name': request.user.username,
                'ip_address': request_audit['ip_address'],
                'user_agent': request_audit['user_agent'],
            },
        )
        status_code = payload.pop('status_code')
        return Response(payload, status=status_code)


class BillingAdminUserSyncStripeSubscriptionAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        before_subscription = (
            Subscription.objects.filter(
                user=user,
            )
            .select_related('plan', 'provider')
            .order_by('-updated_at', '-created_at')
            .first()
        )
        before_credits = (
            UserCredits.objects.filter(
                user=user,
                is_active=True,
            )
            .select_related('subscription__plan')
            .first()
        )
        request_audit = _request_audit_context(request)

        try:
            subscription = SubscriptionService.sync_user_subscription_from_stripe(
                user
            )
        except Exception as exc:
            logger.exception(
                'Failed to sync Stripe subscription for user %s', user.id
            )
            raise serializers.ValidationError(
                {'user_id': f'{exc.__class__.__name__}: {exc}'}
            )

        credits = CreditsService.get_user_credits(user.id)
        queue_billing_audit_event(
            action_type='subscription.sync_stripe',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            target_user_id=user.id,
            target_username=user.username,
            resource_type='subscription',
            resource_id=subscription.id,
            ip_address=request_audit['ip_address'],
            user_agent=request_audit['user_agent'],
            before_data={
                'subscription': _subscription_audit_snapshot(
                    before_subscription
                ),
                'credits': _credits_audit_snapshot(before_credits),
            },
            after_data={
                'subscription': _subscription_audit_snapshot(subscription),
                'credits': _credits_audit_snapshot(credits),
            },
            context={
                'stripe_subscription_id': (
                    subscription.djstripe_subscription.id
                    if subscription.djstripe_subscription
                    else None
                ),
                'plan_slug': subscription.plan.slug if subscription.plan else None,
                'status': subscription.status,
            },
        )
        return Response(
            {
                'subscription': SubscriptionSerializer(subscription).data,
                'credits': UserCreditsSerializer(credits).data,
            },
            status=status.HTTP_200_OK,
        )


class BillingAdminBatchGrantCreditsAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        serializer = BillingBatchGrantCreditsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_ids = list(dict.fromkeys(serializer.validated_data['user_ids']))
        existing_user_ids = set(
            User.objects.filter(id__in=user_ids).values_list('id', flat=True)
        )
        missing_user_ids = [
            user_id for user_id in user_ids if user_id not in existing_user_ids
        ]
        if missing_user_ids:
            raise serializers.ValidationError(
                {'user_ids': f'Unknown user ids: {missing_user_ids}'}
            )

        results = []
        for target_user_id in user_ids:
            target_user = User.objects.get(id=target_user_id)
            before_credits = (
                UserCredits.objects.filter(
                    user=target_user,
                    is_active=True,
                )
                .select_related('subscription__plan')
                .first()
            )
            transaction = CreditsService.grant_bonus_credits(
                user_id=target_user_id,
                amount=serializer.validated_data['amount'],
                reason=serializer.validated_data['reason'],
                operator_id=request.user.id,
            )
            credits = CreditsService.get_user_credits(target_user_id)
            request_audit = _request_audit_context(request)
            queue_billing_audit_event(
                action_type='credits.batch_grant',
                source='admin_api',
                actor_id=request.user.id,
                actor_name=request.user.username,
                target_user_id=target_user.id,
                target_username=target_user.username,
                resource_type='credits_transaction',
                resource_id=transaction.id,
                ip_address=request_audit['ip_address'],
                user_agent=request_audit['user_agent'],
                before_data=_credits_audit_snapshot(before_credits),
                after_data=_credits_audit_snapshot(credits),
                context={
                    'amount': serializer.validated_data['amount'],
                    'reason': serializer.validated_data['reason'],
                    'batch_size': len(user_ids),
                },
            )
            results.append(
                {
                    'user_id': target_user_id,
                    'transaction': CreditsTransactionSerializer(transaction).data,
                    'credits': UserCreditsSerializer(credits).data,
                }
            )

        return Response(
            {
                'count': len(results),
                'results': results,
            },
            status=status.HTTP_201_CREATED,
        )


class BillingAdminTransactionsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = CreditsTransaction.objects.select_related(
            'user',
            'operator',
        ).order_by('-created_at')
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        paginator, page_obj = _paginate(queryset, request)
        serializer = CreditsTransactionSerializer(page_obj.object_list, many=True)
        return Response(
            {
                'count': paginator.count,
                'results': serializer.data,
            }
        )


class BillingAdminPaymentsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = PaymentRecord.objects.select_related(
            'user',
            'subscription__plan',
            'provider',
        ).order_by('-created_at')
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        paginator, page_obj = _paginate(queryset, request)
        serializer = PaymentRecordSerializer(page_obj.object_list, many=True)
        return Response(
            {
                'count': paginator.count,
                'results': serializer.data,
            }
        )


class BillingAdminSubscriptionsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Subscription.objects.select_related(
            'user',
            'plan',
            'provider',
        ).order_by('-created_at')
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        paginator, page_obj = _paginate(queryset, request)
        serializer = SubscriptionSerializer(page_obj.object_list, many=True)
        return Response(
            {
                'count': paginator.count,
                'results': serializer.data,
            }
        )


class BillingAdminPlansAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Plan.objects.prefetch_related(
            Prefetch(
                'plan_prices',
                queryset=PlanPrice.objects.select_related('provider').filter(
                    provider__name='stripe',
                    is_active=True,
                ),
                to_attr='stripe_plan_prices',
            ),
        ).order_by('monthly_price_cents', 'id')
        return Response([_plan_with_stripe_data(plan) for plan in queryset])

    def post(self, request):
        serializer = BillingPlanUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        required_fields = ['name', 'slug', 'description', 'monthly_price_cents']
        missing_fields = [
            field for field in required_fields if field not in data
        ]
        if missing_fields:
            raise serializers.ValidationError(
                {
                    field: 'This field is required.'
                    for field in missing_fields
                }
            )

        status_value = data.get('status')
        if not status_value:
            status_value = (
                Plan.STATUS_ACTIVE if data.get('is_active', True) else Plan.STATUS_DRAFT
            )
        is_internal = data.get('is_internal', False)
        allow_self_purchase = data.get('allow_self_purchase')
        if allow_self_purchase is None:
            allow_self_purchase = (
                status_value == Plan.STATUS_ACTIVE
                and not is_internal
                and data['slug'] != 'free'
            )

        plan = Plan.objects.create(
            name=data['name'],
            slug=data['slug'],
            description=data['description'],
            monthly_price_cents=data['monthly_price_cents'],
            metadata=data.get('metadata') or {},
            status=status_value,
            is_active=data.get('is_active', status_value == Plan.STATUS_ACTIVE),
            is_internal=is_internal,
            allow_self_purchase=allow_self_purchase,
        )
        queue_billing_audit_event(
            action_type='plan.create',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='plan',
            resource_id=plan.id,
            ip_address=_request_audit_context(request)['ip_address'],
            user_agent=_request_audit_context(request)['user_agent'],
            before_data=None,
            after_data=_plan_audit_snapshot(plan),
            context={},
        )
        return Response(_plan_with_stripe_data(plan), status=status.HTTP_201_CREATED)


class BillingAdminPlanDetailAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, plan_id: int) -> Plan:
        return get_object_or_404(Plan, pk=plan_id)

    def get(self, request, plan_id):
        plan = self.get_object(plan_id)
        return Response(_plan_with_stripe_data(plan))

    def put(self, request, plan_id):
        plan = self.get_object(plan_id)
        before_plan = _plan_audit_snapshot(plan)
        serializer = BillingPlanUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'name' in data:
            plan.name = data['name']
        if 'slug' in data:
            plan.slug = data['slug']
        if 'description' in data:
            plan.description = data['description']
        if 'monthly_price_cents' in data:
            plan.monthly_price_cents = data['monthly_price_cents']
        if 'metadata' in data:
            plan.metadata = data['metadata'] or {}
        if 'status' in data:
            plan.status = data['status']
            if 'is_active' not in data:
                plan.is_active = plan.status == Plan.STATUS_ACTIVE
        elif 'is_active' in data:
            plan.status = (
                Plan.STATUS_ACTIVE if data['is_active'] else Plan.STATUS_DRAFT
            )
        if 'allow_self_purchase' in data:
            plan.allow_self_purchase = data['allow_self_purchase']
        if 'is_active' in data:
            plan.is_active = data['is_active']
        if 'is_internal' in data:
            plan.is_internal = data['is_internal']
        plan.save()
        queue_billing_audit_event(
            action_type='plan.update',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='plan',
            resource_id=plan.id,
            ip_address=_request_audit_context(request)['ip_address'],
            user_agent=_request_audit_context(request)['user_agent'],
            before_data=before_plan,
            after_data=_plan_audit_snapshot(plan),
            context={
                'updated_fields': list(data.keys()),
            },
        )
        return Response(_plan_with_stripe_data(plan))

    def patch(self, request, plan_id):
        return self.put(request, plan_id)

    def delete(self, request, plan_id):
        plan = self.get_object(plan_id)
        before_plan = _plan_audit_snapshot(plan)
        plan.delete()
        queue_billing_audit_event(
            action_type='plan.delete',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='plan',
            resource_id=plan_id,
            ip_address=_request_audit_context(request)['ip_address'],
            user_agent=_request_audit_context(request)['user_agent'],
            before_data=before_plan,
            after_data={'deleted': True},
            context={},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BillingAdminPlanSyncStripeAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, plan_id):
        plan = get_object_or_404(Plan, pk=plan_id)
        before_plan = _plan_audit_snapshot(plan)
        request_audit = _request_audit_context(request)
        try:
            sync_result = StripePlanSyncService.sync_plan(plan)
        except ValueError as exc:
            raise serializers.ValidationError({'plan_id': str(exc)})

        after_plan = _plan_audit_snapshot(plan)
        queue_billing_audit_event(
            action_type='plan.sync_stripe',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='plan',
            resource_id=plan.id,
            ip_address=request_audit['ip_address'],
            user_agent=request_audit['user_agent'],
            before_data=before_plan,
            after_data=after_plan,
            context={
                'provider_name': sync_result['provider_name'],
                'provider_product_id': sync_result['provider_product_id'],
                'provider_price_id': sync_result['provider_price_id'],
                'plan_price_id': sync_result['plan_price_id'],
                'created_new_price': sync_result['created_new_price'],
                'deactivated_price_id': sync_result['deactivated_price_id'],
            },
        )
        return Response(
            {
                'plan': after_plan,
                'sync_result': sync_result,
            }
        )


class BillingAdminPaymentCheckAPIView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        serializer = BillingPaymentCheckRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_audit = _request_audit_context(request)
        config = get_billing_config()
        providers = serializer.validated_data.get('providers')
        if providers is None:
            providers = config.payment_check_providers or []
        mode = serializer.validated_data.get('mode', 'report_only')
        result = PaymentCheckService.run(
            providers=providers,
            mode=mode,
            actor_context={
                'source': 'admin_api',
                'actor_id': request.user.id,
                'actor_name': request.user.username,
                'ip_address': request_audit['ip_address'],
                'user_agent': request_audit['user_agent'],
            },
        )
        queue_billing_audit_event(
            action_type='payment_check.run',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='payment_check',
            resource_id='batch',
            ip_address=request_audit['ip_address'],
            user_agent=request_audit['user_agent'],
            before_data={},
            after_data=result,
            context={
                'providers': result.get('requested_providers', []),
                'mode': result.get('mode', mode),
                'totals': result.get('totals', {}),
            },
        )
        return Response(result)


class BillingAdminPaymentRecordBackfillAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = BillingPaymentRecordBackfillRunSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        request_audit = _request_audit_context(request)
        config = get_billing_config()
        backfill_config = dict(getattr(config, 'payment_record_backfill', {}) or {})
        lookback_days = serializer.validated_data.get(
            'lookback_days',
            backfill_config.get('lookback_days', 30) or 30,
        )
        user_id = serializer.validated_data.get('user_id')
        providers = serializer.validated_data.get(
            'providers',
            backfill_config.get('providers') or ['stripe'],
        )
        try:
            result = backfill_payment_records(
                lookback_days=lookback_days,
                user_id=user_id,
                providers=providers,
                source='admin_api',
            )
        except Exception as exc:
            logger.exception('Failed to backfill successful invoice records')
            raise serializers.ValidationError(
                {
                    'detail': (
                        f'{exc.__class__.__name__}: {exc}'
                    )
                }
            )
        queue_billing_audit_event(
            action_type='payment_record.backfill',
            source='admin_api',
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type='payment_record',
            resource_id='batch',
            ip_address=request_audit['ip_address'],
            user_agent=request_audit['user_agent'],
            before_data={},
            after_data=result,
            context={
                'lookback_days': lookback_days,
                'user_id': user_id,
                'created': result.get('created', 0),
                'updated': result.get('updated', 0),
                'skipped': result.get('skipped', 0),
                'processed': result.get('processed', 0),
            },
        )
        return Response(result)


class BillingAdminAuditLogsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = BillingAuditLog.objects.select_related(
            'actor',
            'target_user',
        ).order_by('-created_at')

        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(
                Q(target_user_id=user_id) | Q(actor_id=user_id)
            )

        user_query = (request.query_params.get('user') or '').strip()
        if user_query:
            user_filters = (
                Q(target_username__icontains=user_query)
                | Q(actor_name__icontains=user_query)
                | Q(target_user__username__icontains=user_query)
                | Q(target_user__email__icontains=user_query)
                | Q(actor__username__icontains=user_query)
                | Q(actor__email__icontains=user_query)
            )
            if user_query.isdigit():
                user_filters |= Q(
                    target_user_id=int(user_query)
                ) | Q(actor_id=int(user_query))
            queryset = queryset.filter(user_filters)

        action_type = (request.query_params.get('action_type') or '').strip()
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        source = (request.query_params.get('source') or '').strip()
        if source:
            queryset = queryset.filter(source=source)

        start_date = parse_date(request.query_params.get('start_date') or '')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        end_date = parse_date(request.query_params.get('end_date') or '')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        paginator, page_obj = _paginate(queryset, request)
        serializer = BillingAuditLogSerializer(page_obj.object_list, many=True)
        return Response(
            {
                'count': paginator.count,
                'results': serializer.data,
            }
        )
