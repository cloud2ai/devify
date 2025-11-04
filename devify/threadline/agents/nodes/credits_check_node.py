import logging

from django.conf import settings
from django.utils import timezone

from billing.exceptions import InsufficientCreditsError
from billing.models import EmailCreditsTransaction
from billing.services.credits_service import CreditsService
from threadline.agents.email_state import EmailState, add_node_error
from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.models import EmailMessage

logger = logging.getLogger(__name__)


class CreditsCheckNode(BaseLangGraphNode):
    """
    Check and consume credits for Email Workflow execution
    """

    def __init__(self):
        super().__init__(node_name="credits_check")

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Check credits and consume if available
        """
        if not settings.BILLING_ENABLED:
            logger.info("Billing is disabled, skipping credits check")
            return state

        if not settings.CREDITS_CHECK_ENABLED:
            logger.info("Credits check is disabled, skipping")
            return state

        user_id = state.get('user_id')
        email_id = state.get('id')
        force = state.get('force', False)

        if state.get('credits_consumed'):
            logger.info(
                f"Credits already consumed for email {email_id}"
            )
            return state

        email_message = EmailMessage.objects.get(id=email_id)
        email_uuid = str(email_message.uuid)

        state['email_uuid'] = email_uuid

        if force:
            # Scenario: User force retry (manual retry button in UI)
            # Generate unique idempotency key with timestamp to allow re-charging
            # Use case: User wants to retry after fixing email content or config
            # Result: Will always create a NEW transaction and charge again
            idempotency_key = (
                f"email_{email_uuid}_retry_{int(timezone.now().timestamp())}"
            )
            logger.info(f"Force retry mode, creating new transaction")
        else:
            # Scenario: Normal execution or system error retry
            # Use standard idempotency key for duplicate detection
            # Format: email_{uuid}_workflow_execution (same for all retries)
            idempotency_key = f"email_{email_uuid}_workflow_execution"

            # CRITICAL: Check if this email was already charged before
            # This prevents duplicate charging in several scenarios:
            # 1. Concurrent workflow executions (race condition)
            # 2. Duplicate API calls (user clicks retry button twice)
            # 3. Webhook retries (Stripe resends the same event)
            # 4. System error retry (automatic retry after failure)
            previous_charge = EmailCreditsTransaction.objects.filter(
                email_message=email_message,
                transaction_type='consume',
                idempotency_key=idempotency_key
            ).first()

            if previous_charge:
                # Found a previous charge for this email
                # But we need to check: was it refunded?
                # Because if it was refunded (system error),
                # we SHOULD charge again

                # Check for refunds AFTER the charge was created
                # created_at__gt ensures we only check refunds for THIS charge
                # (not refunds from other unrelated transactions)
                refund_exists = EmailCreditsTransaction.objects.filter(
                    email_message=email_message,
                    transaction_type='refund',
                    created_at__gt=previous_charge.created_at
                ).exists()

                if not refund_exists:
                    # SCENARIO A: Already charged AND NOT refunded
                    # ================================================
                    # This happens when:
                    # - Concurrent requests processing the same email
                    # - User clicks retry button multiple times quickly
                    # - Webhook retry for the same event
                    #
                    # Action: SKIP charging (idempotency protection)
                    # Why: User already paid for this, don't double-charge
                    # Result: Reuse the existing transaction ID
                    logger.info(
                        f"Email {email_id} already charged, skipping"
                    )
                    state['credits_consumed'] = True
                    state['credits_transaction_id'] = str(
                        previous_charge.id
                    )
                    return state
                else:
                    # SCENARIO B: Already charged BUT WAS refunded
                    # ============================================
                    # This happens when:
                    # - First execution failed with system error (LLM timeout)
                    # - ErrorHandlerNode automatically refunded the charge
                    # - User clicks retry (or system auto-retries)
                    #
                    # Action: CONTINUE and charge again
                    # Why: Previous charge was refunded, user should pay for retry
                    # Result: Will create a NEW transaction with the SAME
                    #         idempotency_key
                    #
                    # Example timeline:
                    # 10:00 - Charge 1 credit (transaction #100)
                    # 10:01 - LLM timeout, auto refund (transaction #101)
                    # 10:05 - User retry, charge again (transaction #102)
                    #         Same idempotency_key but allowed because refunded
                    logger.info(
                        "Previous charge was refunded, will charge again"
                    )

        try:
            transaction = CreditsService.consume_credits(
                user_id=int(user_id),
                amount=settings.WORKFLOW_COST_CREDITS,
                reason='workflow_execution',
                email_message_uuid=email_uuid,
                email_message_id=int(email_id),
                idempotency_key=idempotency_key
            )

            state['credits_consumed'] = True
            state['credits_transaction_id'] = str(transaction.id)

            logger.info(
                f"Consumed {settings.WORKFLOW_COST_CREDITS} credit(s) "
                f"for email {email_id} (UUID: {email_uuid}), "
                f"transaction {transaction.id}"
            )

        except InsufficientCreditsError as e:
            logger.warning(
                f"Insufficient credits for email {email_id}: {e}"
            )
            state = add_node_error(
                state,
                self.node_name,
                f"INSUFFICIENT_CREDITS: {str(e)}"
            )

        return state
