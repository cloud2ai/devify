import stripe
from datetime import datetime, timedelta

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from djstripe.models import Customer
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
from billing.serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    UserCreditsSerializer,
    CreditsTransactionSerializer
)
from billing.services.subscription_service import SubscriptionService
from billing.services.credits_service import CreditsService


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Plans are read-only for users
    """
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter plans based on user type
        - Internal users: see all plans (except internal plan itself) but
          cannot purchase
        - Regular users: exclude internal plans
        - Staff users: all plans
        """
        queryset = Plan.objects.filter(is_active=True)

        # Always exclude internal plans from public view
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_internal=False)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Get all active plans with Stripe price information
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        plans_data = serializer.data

        for plan_data in plans_data:
            plan_id = plan_data['id']
            plan_price = PlanPrice.objects.filter(
                plan_id=plan_id,
                provider__name='stripe',
                is_active=True
            ).first()

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
        ).select_related('email_message').order_by('-created_at')

        # Apply pagination
        paginator = Paginator(transactions, page_size)
        page_obj = paginator.get_page(page)

        # Build response data
        results = []
        for transaction in page_obj:
            email_msg = transaction.email_message
            result_item = {
                'id': transaction.id,
                'amount': transaction.amount,
                'subject': email_msg.subject if email_msg else None,
                'chat_id': str(email_msg.uuid) if email_msg else None,
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
        return Response(
            {'detail': 'No active subscription'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """
        Create a new subscription
        """
        plan_id = request.data.get('plan_id')
        provider = request.data.get('provider', 'stripe')

        if not plan_id:
            return Response(
                {'error': 'plan_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscription = SubscriptionService.create_subscription(
                user_id=request.user.id,
                plan_id=plan_id,
                provider=provider
            )
            serializer = self.get_serializer(subscription)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a subscription
        """
        self._check_internal_user(request.user)
        subscription = self.get_object()
        try:
            SubscriptionService.cancel_subscription(subscription.id)
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
            SubscriptionService.resume_subscription(subscription.id)
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
            stripe.api_key = (
                settings.STRIPE_LIVE_SECRET_KEY
                if settings.STRIPE_LIVE_MODE
                else settings.STRIPE_TEST_SECRET_KEY
            )

            customer = Customer.objects.filter(
                subscriber=request.user
            ).first()

            if not customer:
                customer, created = Customer.get_or_create(
                    subscriber=request.user
                )

            frontend_url = settings.FRONTEND_URL

            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=(
                    f'{frontend_url}/billing?success=true&'
                    f'session_id={{CHECKOUT_SESSION_ID}}'
                ),
                cancel_url=f'{frontend_url}/billing?canceled=true',
                metadata={
                    'user_id': request.user.id,
                },
            )

            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })

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
            stripe.api_key = (
                settings.STRIPE_LIVE_SECRET_KEY
                if settings.STRIPE_LIVE_MODE
                else settings.STRIPE_TEST_SECRET_KEY
            )

            customer = Customer.objects.filter(
                subscriber=request.user
            ).first()

            if not customer:
                return Response(
                    {'error': 'No Stripe customer found for this user'},
                    status=status.HTTP_404_NOT_FOUND
                )

            frontend_url = settings.FRONTEND_URL

            portal_session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url=f'{frontend_url}/billing',
            )

            return Response({
                'portal_url': portal_session.url
            })

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
            stripe.api_key = (
                settings.STRIPE_LIVE_SECRET_KEY
                if settings.STRIPE_LIVE_MODE
                else settings.STRIPE_TEST_SECRET_KEY
            )

            # Get current active subscription
            current_subscription = Subscription.objects.filter(
                user=request.user,
                status='active'
            ).first()

            has_djstripe_sub = (
                current_subscription and
                current_subscription.djstripe_subscription
            )
            if not has_djstripe_sub:
                return Response(
                    {'error': 'No active subscription found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update the subscription to use the new price at the end of period
            djstripe_sub = current_subscription.djstripe_subscription

            # Get the subscription from Stripe
            stripe_sub = stripe.Subscription.retrieve(djstripe_sub.id)

            # Get current subscription item
            subscription_item = stripe_sub['items']['data'][0]
            subscription_item_id = subscription_item['id']

            # Update subscription to change price at period end
            stripe.Subscription.modify(
                djstripe_sub.id,
                cancel_at_period_end=False,
                proration_behavior='none',
                items=[{
                    'id': subscription_item_id,
                    'price': stripe_price_id,
                }],
            )

            # Get period end from original subscription item
            effective_date = datetime.fromtimestamp(
                subscription_item['current_period_end']
            ).isoformat()

            return Response({
                'message': 'Downgrade scheduled successfully',
                'effective_date': effective_date
            })

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
