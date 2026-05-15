from __future__ import annotations

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Plan, PlanPrice, Subscription, CreditsTransaction, PaymentRecord, UserCredits
from billing.serializers import (
    CreditsTransactionSerializer,
    PaymentRecordSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    UserCreditsSerializer,
)
from billing.services.config_service import (
    get_billing_config,
    get_public_billing_status,
    serialize_billing_config,
    update_billing_config,
)
from billing.services.credits_service import CreditsService

User = get_user_model()


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
    default_free_credits = serializers.IntegerField(required=False, min_value=0)
    workflow_cost_credits = serializers.IntegerField(required=False, min_value=1)
    auto_refund_system_errors = serializers.BooleanField(required=False)


class BillingPlanUpsertSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    slug = serializers.SlugField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    monthly_price_cents = serializers.IntegerField(required=False, min_value=0)
    metadata = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
    )
    is_active = serializers.BooleanField(required=False)
    is_internal = serializers.BooleanField(required=False)


class BillingGrantCreditsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1, required=False)
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


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


class BillingAdminConfigAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(serialize_billing_config())

    def put(self, request):
        serializer = BillingConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = update_billing_config(
            get_billing_config(),
            serializer.validated_data,
        )
        return Response(serialize_billing_config(config))


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
        queryset = UserCredits.objects.select_related(
            'user',
            'subscription__plan',
        ).order_by('-updated_at')

        search = (request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
            )

        paginator, page_obj = _paginate(queryset, request)
        results = []
        for credits in page_obj.object_list:
            results.append(
                {
                    'id': credits.id,
                    'user_id': credits.user_id,
                    'username': credits.user.username,
                    'email': credits.user.email,
                    'available_credits': credits.available_credits,
                    'base_credits': credits.base_credits,
                    'bonus_credits': credits.bonus_credits,
                    'consumed_credits': credits.consumed_credits,
                    'period_start': credits.period_start,
                    'period_end': credits.period_end,
                    'is_active': credits.is_active,
                    'plan_name': (
                        credits.subscription.plan.name
                        if credits.subscription and credits.subscription.plan
                        else None
                    ),
                    'plan_slug': (
                        credits.subscription.plan.slug
                        if credits.subscription and credits.subscription.plan
                        else None
                    ),
                    'updated_at': credits.updated_at,
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
        transaction = CreditsService.grant_bonus_credits(
            user_id=target_user_id,
            amount=serializer.validated_data['amount'],
            reason=serializer.validated_data['reason'],
            operator_id=request.user.id,
        )
        credits = CreditsService.get_user_credits(
            target_user_id
        )
        return Response(
            {
                'transaction': CreditsTransactionSerializer(transaction).data,
                'credits': UserCreditsSerializer(credits).data,
            },
            status=status.HTTP_201_CREATED,
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
            transaction = CreditsService.grant_bonus_credits(
                user_id=target_user_id,
                amount=serializer.validated_data['amount'],
                reason=serializer.validated_data['reason'],
                operator_id=request.user.id,
            )
            credits = CreditsService.get_user_credits(target_user_id)
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
        queryset = Plan.objects.all().order_by('monthly_price_cents', 'id')
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

        plan = Plan.objects.create(
            name=data['name'],
            slug=data['slug'],
            description=data['description'],
            monthly_price_cents=data['monthly_price_cents'],
            metadata=data.get('metadata') or {},
            is_active=data.get('is_active', True),
            is_internal=data.get('is_internal', False),
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
        if 'is_active' in data:
            plan.is_active = data['is_active']
        if 'is_internal' in data:
            plan.is_internal = data['is_internal']
        plan.save()
        return Response(_plan_with_stripe_data(plan))

    def patch(self, request, plan_id):
        return self.put(request, plan_id)

    def delete(self, request, plan_id):
        plan = self.get_object(plan_id)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
