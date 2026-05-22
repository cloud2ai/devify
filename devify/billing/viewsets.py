from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Prefetch, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.models import (
    Plan,
    PlanPrice,
    Subscription,
    EmailCreditsTransaction
)
from billing.services.audit_service import (
    get_request_ip,
    get_request_user_agent,
    queue_billing_audit_event,
)
from billing.services.payment_provider_gateway import get_billing_gateway
from billing.services.purchase_policy import can_user_purchase
from billing.services.config_service import get_public_billing_status
from billing.serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    UserCreditsSerializer,
    CreditsTransactionSerializer
)
from billing.services.subscription_service import SubscriptionService
from billing.services.credits_service import CreditsService


def _get_credit_usage_display_title(email_msg):
    if not email_msg:
        return None

    canonical_email = (
        email_msg.merged_into
        if getattr(email_msg, 'merged_into_id', None) and email_msg.merged_into
        else email_msg
    )

    return (
        canonical_email.summary_title
        or canonical_email.subject
        or email_msg.summary_title
        or email_msg.subject
        or None
    )


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Plans are read-only for users
    """
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Public billing page should never expose internal plans.
        Admin users manage internal plans through the admin API instead.
        """
        return Plan.objects.filter(status='active', is_internal=False)

    def list(self, request, *args, **kwargs):
        """
        Get all active plans with Stripe price information
        """
        queryset = self.get_queryset().prefetch_related(
            Prefetch(
                'plan_prices',
                queryset=PlanPrice.objects.select_related('provider').filter(
                    provider__name='stripe',
                    is_active=True,
                ),
                to_attr='stripe_plan_prices',
            ),
        )
        plans = list(queryset)
        serializer = self.get_serializer(plans, many=True)

        plans_data = serializer.data

        for plan, plan_data in zip(plans, plans_data):
            prefetched_prices = getattr(plan, 'stripe_plan_prices', None)
            plan_price = prefetched_prices[0] if prefetched_prices else None

            if plan_price:
                plan_data['stripe_price_id'] = plan_price.provider_price_id
                plan_data['stripe_product_id'] = plan_price.provider_product_id
            else:
                plan_data['stripe_price_id'] = None
                plan_data['stripe_product_id'] = None

        return Response(plans_data)


class UserCreditsViewSet(viewsets.ViewSet):
    """
    User credits information and history
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's credits info
        """
        credits = CreditsService.get_user_credits(request.user.id)
        serializer = UserCreditsSerializer(credits)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """
        Simplified balance query
        """
        balance = CreditsService.get_credits_balance(request.user.id)
        return Response(balance)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Credits transaction history
        """
        transactions = CreditsService.get_user_transactions(request.user.id)
        serializer = CreditsTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def usage_stats(self, request):
        """
        Get usage statistics for credits consumption over time
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            try:
                start_date = datetime.fromisoformat(
                    start_date.replace('Z', '+00:00')
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            start_date = timezone.now() - timedelta(days=30)

        if end_date:
            try:
                end_date = datetime.fromisoformat(
                    end_date.replace('Z', '+00:00')
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            end_date = timezone.now()

        transactions = EmailCreditsTransaction.objects.filter(
            user=request.user,
            transaction_type='consume',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            consumed=Sum('amount')
        ).order_by('date')

        stats = [
            {
                'date': item['date'].isoformat(),
                'consumed': item['consumed']
            }
            for item in transactions
        ]

        credits = CreditsService.get_user_credits(request.user.id)

        return Response({
            'stats': stats,
            'total_consumed': credits.consumed_credits,
            'total_available': credits.available_credits,
            'total_credits': credits.total_credits,
            'period_start': credits.period_start,
            'period_end': credits.period_end
        })

    @action(detail=False, methods=['get'])
    def usage_list(self, request):
        """
        Get detailed credit usage list by chats/emails with pagination

        Query params:
        - start_date: ISO format datetime (optional, default: 30 days ago)
        - end_date: ISO format datetime (optional, default: now)
        - page: Page number (optional, default: 1)
        - page_size: Items per page (optional, default: 10)

        Returns paginated list of credit transactions with chat info
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # Parse and validate start_date
        if start_date:
            try:
                start_date = datetime.fromisoformat(
                    start_date.replace('Z', '+00:00')
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Default to 30 days ago if not specified
            start_date = timezone.now() - timedelta(days=30)

        # Parse and validate end_date
        if end_date:
            try:
                end_date = datetime.fromisoformat(
                    end_date.replace('Z', '+00:00')
                )
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Default to now if not specified
            end_date = timezone.now()

        # Query credit transactions with related email message
        transactions = EmailCreditsTransaction.objects.filter(
            user=request.user,
            transaction_type='consume',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related(
            'email_message',
            'email_message__merged_into',
        ).order_by('-created_at')

        # Apply pagination
        paginator = Paginator(transactions, page_size)
        page_obj = paginator.get_page(page)

        # Build response data
        results = []
        for transaction in page_obj:
            email_msg = transaction.email_message
            canonical_email = (
                email_msg.merged_into
                if email_msg and email_msg.merged_into_id
                else email_msg
            )
            result_item = {
                'id': transaction.id,
                'amount': transaction.amount,
                'display_title': _get_credit_usage_display_title(email_msg),
                'subject': email_msg.subject if email_msg else None,
                'summary_title': (
                    email_msg.summary_title if email_msg else None
                ),
                'chat_id': (
                    str(canonical_email.uuid) if canonical_email else None
                ),
                'status': email_msg.status if email_msg else None,
                'created_at': transaction.created_at.isoformat()
            }
            results.append(result_item)

        return Response({
            'count': paginator.count,
            'results': results
        })


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    User subscription management
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def _check_internal_user(self, user):
        """
        Check if user has internal plan subscription
        If yes, raise PermissionDenied
        """
        has_internal_plan = Subscription.objects.filter(
            user=user,
            status='active',
            plan__is_internal=True
        ).exists()
        if has_internal_plan:
            raise PermissionDenied(
                'Internal plan users cannot modify subscriptions. '
                'Please contact administrator.'
            )

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's active subscription
        """
        subscription = SubscriptionService.get_active_subscription(
            request.user.id
        )
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        return Response(None)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a subscription
        """
        self._check_internal_user(request.user)
        subscription = self.get_object()
        try:
            before_data = SubscriptionSerializer(subscription).data
            SubscriptionService.cancel_subscription(subscription.id)
            subscription.refresh_from_db()
            queue_billing_audit_event(
                action_type='subscription.cancel',
                source='user_api',
                actor_id=request.user.id,
                actor_name=request.user.username,
                target_user_id=request.user.id,
                target_username=request.user.username,
                resource_type='subscription',
                resource_id=subscription.id,
                ip_address=get_request_ip(request),
                user_agent=get_request_user_agent(request),
                before_data=before_data,
                after_data=SubscriptionSerializer(subscription).data,
                context={'subscription_id': subscription.id},
            )
            return Response({'status': 'cancelled'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """
        Resume a cancelled subscription
        """
        self._check_internal_user(request.user)
        subscription = self.get_object()
        try:
            before_data = SubscriptionSerializer(subscription).data
            SubscriptionService.resume_subscription(subscription.id)
            subscription.refresh_from_db()
            queue_billing_audit_event(
                action_type='subscription.resume',
                source='user_api',
                actor_id=request.user.id,
                actor_name=request.user.username,
                target_user_id=request.user.id,
                target_username=request.user.username,
                resource_type='subscription',
                resource_id=subscription.id,
                ip_address=get_request_ip(request),
                user_agent=get_request_user_agent(request),
                before_data=before_data,
                after_data=SubscriptionSerializer(subscription).data,
                context={'subscription_id': subscription.id},
            )
            return Response({'status': 'resumed'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def create_checkout_session(self, request):
        """
        Create a Stripe Checkout Session for subscription
        """
        self._check_internal_user(request.user)
        price_id = request.data.get('price_id')

        if not price_id:
            return Response(
                {'error': 'price_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan_price = (
                PlanPrice.objects.select_related('plan')
                .filter(
                    provider__name='stripe',
                    provider_price_id=price_id,
                    is_active=True,
                )
                .first()
            )
            if not plan_price:
                return Response(
                    {'error': 'Invalid price_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not can_user_purchase(
                plan_price.plan,
                'stripe',
                get_public_billing_status(),
            ):
                return Response(
                    {'error': 'This plan is not available for self-purchase'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            gateway = get_billing_gateway('stripe')
            result = gateway.create_checkout_session(request.user, price_id)
            if 'error' in result:
                status_code = (
                    status.HTTP_409_CONFLICT
                    if 'Multiple Stripe customers' in result['error']
                    else status.HTTP_400_BAD_REQUEST
                )
                return Response(result, status=status_code)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_portal_session(self, request):
        """
        Create a Stripe Customer Portal Session
        """
        self._check_internal_user(request.user)
        try:
            gateway = get_billing_gateway('stripe')
            result = gateway.create_portal_session(request.user)
            if 'error' in result:
                status_code = (
                    status.HTTP_409_CONFLICT
                    if 'Multiple Stripe customers' in result['error']
                    else status.HTTP_404_NOT_FOUND
                )
                return Response(result, status=status_code)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['post'],
        url_path='schedule-downgrade'
    )
    def schedule_downgrade(self, request):
        """
        Schedule a subscription downgrade
        Effective at the end of current period
        """
        self._check_internal_user(request.user)
        stripe_price_id = request.data.get('stripe_price_id')

        if not stripe_price_id:
            return Response(
                {'error': 'stripe_price_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            current_subscription = Subscription.objects.filter(
                user=request.user,
                status='active'
            ).first()
            gateway = get_billing_gateway('stripe')
            result = gateway.schedule_downgrade(
                current_subscription,
                stripe_price_id,
            )
            if 'error' in result:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to schedule downgrade: {str(e)}",
                exc_info=True
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
