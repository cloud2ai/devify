from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.models import (
    Plan,
    Subscription,
    UserCredits,
    CreditsTransaction
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


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    User subscription management
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

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
        subscription = self.get_object()
        try:
            SubscriptionService.cancel_subscription(subscription.id)
            return Response({'status': 'cancelled'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
