from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from billing.fields import EncryptedTextField


class Plan(models.Model):
    """
    Subscription plan definition
    """
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
    ]

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
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        blank=True,
        default=STATUS_DRAFT,
        help_text='Plan lifecycle status: draft or active',
    )
    is_active = models.BooleanField(default=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal plan for staff/partners, not visible to public"
    )
    allow_self_purchase = models.BooleanField(
        default=False,
        help_text='Whether users can purchase this plan directly',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_plan'
        verbose_name = 'Plan'
        verbose_name_plural = 'Plans'
        ordering = ['monthly_price_cents']

    def __str__(self):
        return f"{self.name} (${self.monthly_price_cents / 100:.2f}/mo)"

    def save(self, *args, **kwargs):
        if not self.status:
            self.status = (
                self.STATUS_ACTIVE if self.is_active else self.STATUS_DRAFT
            )
        super().save(*args, **kwargs)


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


class BillingAuditLog(models.Model):
    """
    Central audit log for billing-related write operations.

    This model stores the who/what/when/where of billing mutations and keeps
    flexible before/after/context payloads in JSON for future expansion.
    """

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_audit_logs_as_actor',
    )
    actor_name = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text='Snapshot of the operator name at write time',
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_audit_logs',
    )
    target_username = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text='Snapshot of the target user name at write time',
    )
    action_type = models.CharField(max_length=64, db_index=True)
    source = models.CharField(
        max_length=32,
        default='system',
        db_index=True,
    )
    resource_type = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
    )
    resource_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    before_data = models.JSONField(default=dict)
    after_data = models.JSONField(default=dict)
    context = models.JSONField(default=dict)
    event_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Idempotency key for audit write retries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_audit_log'
        verbose_name = 'Billing Audit Log'
        verbose_name_plural = 'Billing Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['source', 'created_at']),
            models.Index(fields=['target_user', 'created_at']),
        ]

    def __str__(self):
        return (
            f"{self.action_type} "
            f"actor={self.actor_name or self.actor_id or '-'} "
            f"target={self.target_username or self.target_user_id or '-'}"
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
    Payment provider definition for billing flows.

    Examples:
    - platform: admin-granted or internal billing source
    - stripe: card-based payment provider
    - alipay / wechat: future external payment providers
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g., 'platform', 'stripe', 'alipay', 'wechat'"
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


class BillingConfig(models.Model):
    """
    Singleton billing configuration for admin control plane.
    """

    singleton_key = models.CharField(
        max_length=32,
        unique=True,
        default='default',
    )
    stripe_live_mode = models.BooleanField(default=False)
    stripe_publishable_key = models.CharField(max_length=255, blank=True)
    stripe_live_secret_key = EncryptedTextField(blank=True, default='')
    stripe_test_secret_key = EncryptedTextField(blank=True, default='')
    stripe_webhook_secret = EncryptedTextField(blank=True, default='')
    payment_callback_url = models.CharField(max_length=255, blank=True, default='')
    self_purchase_enabled = models.BooleanField(default=False)
    payment_check_enabled = models.BooleanField(default=False)
    payment_check_providers = models.JSONField(default=list, blank=True)
    payment_check_schedule = models.CharField(max_length=255, blank=True, default='')
    payment_record_backfill = models.JSONField(default=dict, blank=True)
    enabled_providers = models.JSONField(default=list, blank=True)
    default_free_credits = models.IntegerField(default=10)
    workflow_cost_credits = models.IntegerField(default=1)
    auto_refund_system_errors = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_config'
        verbose_name = 'Billing Config'
        verbose_name_plural = 'Billing Config'
        ordering = ['-updated_at']

    def __str__(self):
        return 'Billing Config'


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
