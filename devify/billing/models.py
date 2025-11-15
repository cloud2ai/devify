from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Plan(models.Model):
    """
    Subscription plan definition
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    monthly_price_cents = models.IntegerField(
        help_text="Price in cents (e.g., 2999 for $29.99)"
    )
    metadata = models.JSONField(
        default=dict,
        help_text=(
            "Flexible configuration: credits_per_period, period_days, "
            "workflow_cost_credits, max_email_length, "
            "max_attachment_count, storage_quota_mb"
        )
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_plan'
        verbose_name = 'Plan'
        verbose_name_plural = 'Plans'
        ordering = ['monthly_price_cents']

    def __str__(self):
        return f"{self.name} (${self.monthly_price_cents / 100:.2f}/mo)"


class UserCredits(models.Model):
    """
    User's current credits balance and period information
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credits'
    )
    djstripe_customer = models.ForeignKey(
        'djstripe.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to dj-stripe Customer for sync"
    )
    subscription = models.ForeignKey(
        'Subscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_credits'
    )
    base_credits = models.IntegerField(
        default=0,
        help_text="Credits from subscription plan"
    )
    bonus_credits = models.IntegerField(
        default=0,
        help_text="Bonus credits from promotions or compensation"
    )
    consumed_credits = models.IntegerField(
        default=0,
        help_text="Total credits consumed in current period"
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_user_credits'
        verbose_name = 'User Credits'
        verbose_name_plural = 'User Credits'
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_active=True),
                name='unique_active_user_credits'
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username}: "
            f"{self.available_credits}/{self.total_credits} credits"
        )

    @property
    def available_credits(self):
        """
        Calculate available credits
        """
        return self.base_credits + self.bonus_credits - self.consumed_credits

    @property
    def total_credits(self):
        """
        Calculate total credits
        """
        return self.base_credits + self.bonus_credits


class CreditsTransaction(models.Model):
    """
    General credits transaction for non-business scenarios
    (admin grants, bonuses, compensations, etc.)
    """
    TRANSACTION_TYPE_CHOICES = [
        ('grant', 'Grant'),
        ('bonus', 'Bonus'),
        ('compensation', 'Compensation'),
        ('refund', 'Refund'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credits_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=500)
    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_credits'
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_credits_transaction'
        verbose_name = 'Credits Transaction'
        verbose_name_plural = 'Credits Transactions'
        indexes = [
            models.Index(
                fields=['user', 'transaction_type', 'created_at']
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.username}: {self.transaction_type} "
            f"{self.amount} credits"
        )


class EmailCreditsTransaction(models.Model):
    """
    Credits transaction specifically for Email Workflow execution
    Separated from general credits transaction to avoid hardcoding
    """
    TRANSACTION_TYPE_CHOICES = [
        ('consume', 'Consume'),
        ('refund', 'Refund'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_credits_transactions'
    )
    email_message = models.ForeignKey(
        'threadline.EmailMessage',
        on_delete=models.CASCADE,
        related_name='credits_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )
    amount = models.IntegerField(default=1)
    reason = models.CharField(
        max_length=500,
        default='workflow_execution'
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=(
            "Idempotency key format: email_{uuid}_workflow_execution "
            "or email_{uuid}_retry_{timestamp}"
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_email_credits_transaction'
        verbose_name = 'Email Credits Transaction'
        verbose_name_plural = 'Email Credits Transactions'
        indexes = [
            models.Index(
                fields=['user', 'transaction_type', 'created_at']
            ),
            models.Index(fields=['idempotency_key']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.username}: {self.transaction_type} "
            f"{self.amount} credits for email {self.email_message_id}"
        )


class PaymentProvider(models.Model):
    """
    Payment provider definition (Stripe, Alipay, WeChat, etc.)
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g., 'stripe', 'alipay', 'wechat'"
    )
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_payment_provider'
        verbose_name = 'Payment Provider'
        verbose_name_plural = 'Payment Providers'

    def __str__(self):
        return self.display_name


class PlanPrice(models.Model):
    """
    Plan price mapping for different payment providers
    """
    INTERVAL_CHOICES = [
        ('month', 'Month'),
        ('year', 'Year'),
    ]

    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='plan_prices'
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.CASCADE,
        related_name='plan_prices'
    )
    provider_product_id = models.CharField(
        max_length=255,
        help_text="Stripe Product ID"
    )
    provider_price_id = models.CharField(
        max_length=255,
        help_text="Stripe Price ID"
    )
    currency = models.CharField(max_length=3, default='USD')
    interval = models.CharField(
        max_length=10,
        choices=INTERVAL_CHOICES,
        default='month'
    )
    unit_amount_cents = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_plan_price'
        verbose_name = 'Plan Price'
        verbose_name_plural = 'Plan Prices'
        unique_together = ['plan', 'provider', 'interval']

    def __str__(self):
        return (
            f"{self.plan.name} - {self.provider.name} "
            f"({self.currency} {self.unit_amount_cents / 100:.2f}/"
            f"{self.interval})"
        )


class Subscription(models.Model):
    """
    User subscription status
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    djstripe_subscription = models.ForeignKey(
        'djstripe.Subscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to dj-stripe Subscription"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_subscription'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(
                fields=['user', 'status', 'current_period_end']
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.username} - {self.plan.name} "
            f"({self.status})"
        )


class PaymentRecord(models.Model):
    """
    Payment transaction record
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_records'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_records'
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name='payment_records'
    )
    provider_payment_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_payment_record'
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'
        indexes = [
            models.Index(fields=['provider_payment_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.username}: {self.currency} "
            f"{self.amount_cents / 100:.2f} ({self.status})"
        )


class EmailWorkflowUsage(models.Model):
    """
    Email Workflow API usage metrics linked to credits transaction

    This model has a one-to-one relationship with EmailCreditsTransaction.
    All email and user information is accessible via credits_transaction.

    Relationship:
    - 1 EmailCreditsTransaction → 1 EmailWorkflowUsage
    - usage.credits_transaction.email_message → EmailMessage
    - usage.credits_transaction.user → User
    """
    credits_transaction = models.OneToOneField(
        'EmailCreditsTransaction',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='workflow_usage',
        help_text="One-to-one mapping with credits transaction"
    )

    llm_call_count = models.IntegerField(default=0)
    llm_success_count = models.IntegerField(default=0)
    llm_total_input_tokens = models.IntegerField(default=0)
    llm_total_output_tokens = models.IntegerField(default=0)
    llm_total_tokens = models.IntegerField(default=0)

    ocr_call_count = models.IntegerField(default=0)
    ocr_success_count = models.IntegerField(default=0)
    ocr_total_images = models.IntegerField(default=0)

    llm_calls_detail = models.JSONField(
        default=list,
        help_text=(
            "List of all LLM calls with tokens, success status, errors"
        )
    )
    ocr_calls_detail = models.JSONField(
        default=list,
        help_text=(
            "List of all OCR calls with filenames, success status, errors"
        )
    )

    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Estimated cost based on pricing config"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_email_workflow_usage'
        verbose_name = 'Email Workflow Usage'
        verbose_name_plural = 'Email Workflow Usages'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Transaction {self.credits_transaction_id}: "
            f"LLM {self.llm_call_count} calls "
            f"({self.llm_total_tokens} tokens), "
            f"OCR {self.ocr_call_count} calls "
            f"({self.ocr_total_images} pages)"
        )
