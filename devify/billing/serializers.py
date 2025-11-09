from rest_framework import serializers

from billing.models import (
    Plan,
    PlanPrice,
    UserCredits,
    Subscription,
    CreditsTransaction,
    EmailCreditsTransaction
)


class PlanSerializer(serializers.ModelSerializer):
    """
    Plan serializer
    """
    credits_per_period = serializers.SerializerMethodField()
    period_days = serializers.SerializerMethodField()
    monthly_price = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'monthly_price_cents',
            'monthly_price',
            'credits_per_period',
            'period_days',
            'metadata',
            'is_active'
        ]

    def get_credits_per_period(self, obj):
        return obj.metadata.get('credits_per_period', 0)

    def get_period_days(self, obj):
        return obj.metadata.get('period_days', 30)

    def get_monthly_price(self, obj):
        return f"${obj.monthly_price_cents / 100:.2f}"


class UserCreditsSerializer(serializers.ModelSerializer):
    """
    User credits serializer
    Updated to reflect new credit limits
    """
    available_credits = serializers.IntegerField(read_only=True)
    total_credits = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    plan_metadata = serializers.SerializerMethodField()

    class Meta:
        model = UserCredits
        fields = [
            'user',
            'username',
            'base_credits',
            'bonus_credits',
            'consumed_credits',
            'available_credits',
            'total_credits',
            'period_start',
            'period_end',
            'is_active',
            'plan_metadata'
        ]
        read_only_fields = [
            'user',
            'consumed_credits',
            'period_start',
            'period_end'
        ]

    def get_plan_metadata(self, obj):
        subscription = Subscription.objects.filter(
            user=obj.user,
            status='active'
        ).select_related('plan').first()
        if subscription and subscription.plan:
            return subscription.plan.metadata
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Subscription serializer
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_slug = serializers.CharField(source='plan.slug', read_only=True)
    plan_metadata = serializers.SerializerMethodField()
    provider_name = serializers.CharField(
        source='provider.display_name',
        read_only=True
    )
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        model = Subscription
        fields = [
            'id',
            'user',
            'username',
            'plan',
            'plan_name',
            'plan_slug',
            'plan_metadata',
            'provider',
            'provider_name',
            'status',
            'current_period_start',
            'current_period_end',
            'auto_renew',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'user',
            'djstripe_subscription',
            'created_at',
            'updated_at'
        ]

    def get_plan_metadata(self, obj):
        if obj.plan:
            return obj.plan.metadata
        return None


class CreditsTransactionSerializer(serializers.ModelSerializer):
    """
    Credits transaction serializer
    """
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    operator_username = serializers.CharField(
        source='operator.username',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = CreditsTransaction
        fields = [
            'id',
            'user',
            'username',
            'transaction_type',
            'amount',
            'reason',
            'operator',
            'operator_username',
            'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmailCreditsTransactionSerializer(serializers.ModelSerializer):
    """
    Email credits transaction serializer
    """
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        model = EmailCreditsTransaction
        fields = [
            'id',
            'user',
            'username',
            'email_message',
            'transaction_type',
            'amount',
            'reason',
            'idempotency_key',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
