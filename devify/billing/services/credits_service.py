from datetime import timedelta
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from billing.exceptions import InsufficientCreditsError
from billing.models import (
    CreditsTransaction,
    EmailCreditsTransaction,
    Plan,
    UserCredits,
)

logger = logging.getLogger(__name__)


class CreditsService:
    """
    Credits management service with Django best practices
    """

    @staticmethod
    def get_user_credits(user_id: int) -> UserCredits:
        """
        Get or create user credits with free tier defaults
        """
        credits, created = UserCredits.objects.get_or_create(
            user_id=user_id,
            defaults={
                'base_credits': settings.DEFAULT_FREE_CREDITS,
                'bonus_credits': 0,
                'consumed_credits': 0,
                'period_start': timezone.now(),
                'period_end': timezone.now() + timedelta(days=30),
                'is_active': True
            }
        )

        if created:
            logger.info(
                f"Created new credits for user {user_id} with "
                f"{settings.DEFAULT_FREE_CREDITS} free credits"
            )

        return credits

    @staticmethod
    def check_credits(user_id: int, required_amount: int = 1) -> bool:
        """
        Check if user has enough credits
        """
        credits = CreditsService.get_user_credits(user_id)
        return credits.available_credits >= required_amount

    @staticmethod
    @transaction.atomic
    def consume_credits(
        user_id: int,
        amount: int = 1,
        reason: str = 'workflow_execution',
        email_message_uuid: str = None,
        email_message_id: int = None,
        idempotency_key: str = None
    ) -> EmailCreditsTransaction:
        """
        Consume credits with idempotency and race condition protection

        Best practices applied:
        1. transaction.atomic for ACID guarantees
        2. select_for_update() for row-level locking
        3. F() expression for atomic database-level updates
        4. Idempotency key for duplicate prevention
        """
        if idempotency_key:
            existing = EmailCreditsTransaction.objects.filter(
                idempotency_key=idempotency_key
            ).first()

            if existing:
                logger.info(
                    f"Transaction {idempotency_key} already exists "
                    "(idempotent)"
                )
                return existing

        user_credits = UserCredits.objects.select_for_update().get(
            user_id=user_id
        )

        if user_credits.available_credits < amount:
            raise InsufficientCreditsError(
                f"User {user_id} has insufficient credits: "
                f"available={user_credits.available_credits}, "
                f"required={amount}"
            )

        UserCredits.objects.filter(
            user_id=user_id
        ).update(
            consumed_credits=F('consumed_credits') + amount
        )

        user_credits.refresh_from_db()

        transaction_record = EmailCreditsTransaction.objects.create(
            user_id=user_id,
            email_message_id=email_message_id,
            transaction_type='consume',
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key
        )

        logger.info(
            f"Consumed {amount} credits for user {user_id}, "
            f"remaining: {user_credits.available_credits}"
        )

        return transaction_record

    @staticmethod
    @transaction.atomic
    def refund_credits(
        transaction_id: int,
        reason: str = ''
    ):
        """
        Refund credits with same atomic guarantees
        """
        email_transaction = (
            EmailCreditsTransaction.objects
            .select_for_update()
            .get(id=transaction_id)
        )

        existing_refund = EmailCreditsTransaction.objects.filter(
            email_message_id=email_transaction.email_message_id,
            transaction_type='refund',
            idempotency_key=f"refund_{transaction_id}"
        ).exists()

        if existing_refund:
            logger.warning(
                f"Transaction {transaction_id} already refunded"
            )
            return

        UserCredits.objects.filter(
            user_id=email_transaction.user_id
        ).update(
            consumed_credits=F('consumed_credits') - email_transaction.amount
        )

        EmailCreditsTransaction.objects.create(
            user_id=email_transaction.user_id,
            email_message_id=email_transaction.email_message_id,
            transaction_type='refund',
            amount=email_transaction.amount,
            reason=reason or f"Refund of transaction {transaction_id}",
            idempotency_key=f"refund_{transaction_id}"
        )

        logger.info(
            f"Refunded {email_transaction.amount} credits "
            f"for transaction {transaction_id}"
        )

    @staticmethod
    def get_credits_balance(user_id: int) -> dict:
        """
        Get simplified balance
        """
        credits = CreditsService.get_user_credits(user_id)
        return {
            'available_credits': credits.available_credits,
            'base_credits': credits.base_credits,
            'bonus_credits': credits.bonus_credits,
            'consumed_credits': credits.consumed_credits,
            'period_end': credits.period_end.isoformat()
        }

    @staticmethod
    def get_user_transactions(user_id: int):
        """
        Get user's credits transaction history
        """
        return CreditsTransaction.objects.filter(
            user_id=user_id
        ).order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def reset_period_credits(user_id: int):
        """
        Reset credits for a new billing period
        """
        credits = UserCredits.objects.select_for_update().get(
            user_id=user_id
        )

        plan_credits = 0
        if credits.subscription and credits.subscription.plan:
            plan_credits = (
                credits.subscription.plan.metadata
                .get('credits_per_period', 0)
            )

        period_days = 30
        if credits.subscription and credits.subscription.plan:
            period_days = (
                credits.subscription.plan.metadata
                .get('period_days', 30)
            )

        UserCredits.objects.filter(
            user_id=user_id
        ).update(
            base_credits=plan_credits,
            consumed_credits=0,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=period_days)
        )

        logger.info(
            f"Reset credits for user {user_id}: "
            f"{plan_credits} base credits"
        )

    @staticmethod
    @transaction.atomic
    def grant_bonus_credits(
        user_id: int,
        amount: int,
        reason: str,
        operator_id: int = None
    ):
        """
        Grant bonus credits to user
        """
        UserCredits.objects.filter(
            user_id=user_id
        ).update(
            bonus_credits=F('bonus_credits') + amount
        )

        CreditsTransaction.objects.create(
            user_id=user_id,
            transaction_type='bonus',
            amount=amount,
            reason=reason,
            operator_id=operator_id
        )

        logger.info(
            f"Granted {amount} bonus credits to user {user_id}: "
            f"{reason}"
        )
