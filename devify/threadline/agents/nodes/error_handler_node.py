"""
Error handling node for automatic credit refund decisions.

This node is specifically added for the billing system to handle
automatic credit refunds based on error classification.

Key responsibilities:
- Classify workflow errors (system error vs user error)
- Automatically refund credits for system errors
- Skip refund for user errors
- Improve user experience by refunding for our mistakes

This node only executes when there are errors in the workflow.
"""

import logging

from django.conf import settings

from billing.services.credits_service import CreditsService
from billing.services.error_classifier import ErrorClassifier
from threadline.agents.email_state import EmailState
from threadline.agents.nodes.base_node import BaseLangGraphNode

logger = logging.getLogger(__name__)


class ErrorHandlerNode(BaseLangGraphNode):
    """
    Centralized error handling and automatic credit refund logic.

    This node is part of the billing system and handles:
    1. Error classification (system error vs user error)
    2. Automatic refund for system errors
    3. No refund for user errors

    Position in workflow: After Issue node (conditional routing)
    Only executes when: has_node_errors(state) == True
    """

    def __init__(self):
        super().__init__(node_name="error_handler")

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Analyze workflow errors and refund credits if caused by system issues.

        Decision flow:
        1. Check if billing system is enabled → Skip if disabled
        2. Check if auto refund is enabled → Skip if disabled
        3. Check if credits were consumed → Skip if no charge
        4. Collect all error messages from failed nodes
        5. Classify errors (system vs user)
        6. Refund only for system errors

        Args:
            state: EmailState containing node_errors and credits info

        Returns:
            EmailState with credits_refunded flag if refund occurred
        """
        # STEP 1: Check if billing system is enabled
        # If disabled, this node does nothing (safe for testing)
        if not settings.BILLING_ENABLED:
            logger.info("Billing is disabled, skipping error handler")
            return state

        # STEP 2: Check if auto refund feature is enabled
        # Can be disabled to require manual review of all refunds
        if not settings.AUTO_REFUND_SYSTEM_ERRORS:
            logger.info(
                "Auto refund is disabled, skipping credit refund"
            )
            return state

        # STEP 3: Check if credits were actually consumed
        # No consumption = nothing to refund
        if not state.get('credits_consumed'):
            logger.info("No credits consumed, nothing to refund")
            return state

        # STEP 4: Verify transaction ID exists
        # Should always exist if credits_consumed=True
        # Warning if missing (data inconsistency)
        if not state.get('credits_transaction_id'):
            logger.warning(
                "Credits consumed but no transaction ID found"
            )
            return state

        # STEP 5: Check if there are any errors to process
        # node_errors format: {'node_name': [{'error_message': '...'}]}
        node_errors = state.get('node_errors', {})
        if not node_errors:
            logger.info("No errors to handle")
            return state

        # STEP 6: Collect all error messages from all failed nodes
        # Combine all errors into a single string for classification
        # Example: "OCR timeout; LLM API rate limit exceeded"
        all_errors = []
        for node_name, errors in node_errors.items():
            for error in errors:
                all_errors.append(error.get('error_message', ''))

        error_messages = ' '.join(all_errors)

        # STEP 7: Classify error type and decide refund eligibility
        # System errors (our fault) → Refund
        # User errors (user's fault) → No refund
        if ErrorClassifier.is_system_error(error_messages):
            # REFUND SCENARIO: System error detected
            # Examples: timeout, connection error, 500 server error,
            #           rate limit, API unavailable
            # Action: Automatically refund the consumed credits
            # Why: User shouldn't pay for our service failures
            try:
                CreditsService.refund_credits(
                    transaction_id=int(
                        state['credits_transaction_id']
                    ),
                    reason=f'system_error: {error_messages[:200]}'
                )
                state['credits_refunded'] = True
                logger.info(
                    f"Refunded credits for email {state.get('id')} "
                    f"due to system error"
                )
            except Exception as e:
                # Refund failure is logged but doesn't block workflow
                # Admin can manually refund later
                logger.error(f"Failed to refund credits: {e}")
        else:
            # NO REFUND SCENARIO: User error detected
            # Examples: invalid format, email too long, unsupported file type
            # Action: No refund (user should fix their input)
            # Why: User caused the error, should pay for the attempt
            logger.info(
                f"User error detected, no refund needed: "
                f"{error_messages[:100]}"
            )

        return state
