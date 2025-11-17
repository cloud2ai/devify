from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget
from django.db import models

from billing.models import (
    Plan,
    PlanPrice,
    UserCredits,
    CreditsTransaction,
    EmailCreditsTransaction,
    Subscription,
    PaymentRecord,
    PaymentProvider,
    EmailWorkflowUsage,
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'monthly_price_display',
        'credits_per_period',
        'is_active',
        'is_internal'
    ]
    list_filter = ['is_active', 'is_internal']
    search_fields = ['name', 'slug']
    readonly_fields = ['created_at', 'updated_at']

    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

    def monthly_price_display(self, obj):
        return f"${obj.monthly_price_cents / 100:.2f}"
    monthly_price_display.short_description = 'Monthly Price'

    def credits_per_period(self, obj):
        return obj.metadata.get('credits_per_period', 0)
    credits_per_period.short_description = 'Credits/Period'


@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'available_credits_display',
        'base_credits',
        'bonus_credits',
        'consumed_credits',
        'period_end',
        'is_active'
    ]
    list_filter = ['is_active', 'period_end']
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'consumed_credits',
        'created_at',
        'updated_at',
        'available_credits_display'
    ]

    def available_credits_display(self, obj):
        return obj.available_credits
    available_credits_display.short_description = 'Available Credits'


@admin.register(EmailCreditsTransaction)
class EmailCreditsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'email_message',
        'transaction_type',
        'amount',
        'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = [
        'user__username',
        'email_message__id',
        'reason'
    ]
    readonly_fields = [
        'user',
        'email_message',
        'transaction_type',
        'amount',
        'reason',
        'idempotency_key',
        'created_at'
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditsTransaction)
class CreditsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'transaction_type',
        'amount',
        'reason',
        'operator',
        'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['created_at']

    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'plan',
        'status',
        'current_period_start',
        'current_period_end',
        'auto_renew'
    ]
    list_filter = ['status', 'auto_renew', 'plan']
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'djstripe_subscription',
        'created_at',
        'updated_at'
    ]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'provider',
        'amount_display',
        'currency',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['user__username', 'provider_payment_id']
    readonly_fields = [
        'provider_payment_id',
        'metadata',
        'created_at',
        'updated_at'
    ]

    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

    def amount_display(self, obj):
        return f"${obj.amount_cents / 100:.2f}"
    amount_display.short_description = 'Amount'


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PlanPrice)
class PlanPriceAdmin(admin.ModelAdmin):
    list_display = [
        'plan',
        'provider',
        'currency',
        'unit_amount_display',
        'interval',
        'is_active'
    ]
    list_filter = ['provider', 'currency', 'interval', 'is_active']
    search_fields = ['plan__name', 'provider__name']
    readonly_fields = ['created_at', 'updated_at']

    def unit_amount_display(self, obj):
        return f"{obj.unit_amount_cents / 100:.2f}"
    unit_amount_display.short_description = 'Unit Amount'


@admin.register(EmailWorkflowUsage)
class EmailWorkflowUsageAdmin(admin.ModelAdmin):
    list_display = [
        'credits_transaction',
        'email_display',
        'user_display',
        'llm_call_count',
        'llm_total_tokens',
        'ocr_call_count',
        'ocr_total_images',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'credits_transaction__email_message__id',
        'credits_transaction__user__username'
    ]
    readonly_fields = [
        'credits_transaction',
        'email_display',
        'user_display',
        'transaction_type_display',
        'llm_call_count',
        'llm_success_count',
        'llm_total_input_tokens',
        'llm_total_output_tokens',
        'llm_total_tokens',
        'ocr_call_count',
        'ocr_success_count',
        'ocr_total_images',
        'llm_calls_detail',
        'ocr_calls_detail',
        'estimated_cost_usd',
        'created_at'
    ]

    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

    @admin.display(description='Email')
    def email_display(self, obj):
        return obj.credits_transaction.email_message

    @admin.display(description='User')
    def user_display(self, obj):
        return obj.credits_transaction.user

    @admin.display(description='Transaction Type')
    def transaction_type_display(self, obj):
        return obj.credits_transaction.transaction_type

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
