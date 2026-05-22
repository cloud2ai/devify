import pytest

from billing.services.config_service import get_billing_config
from threadline.agents.nodes.error_handler_node import ErrorHandlerNode


@pytest.mark.django_db
def test_error_handler_skips_refund_when_runtime_config_disables_auto_refund(
    mocker,
):
    config = get_billing_config()
    original_auto_refund = config.auto_refund_system_errors
    config.auto_refund_system_errors = False
    config.save(update_fields=['auto_refund_system_errors'])

    refund_credits = mocker.patch(
        'threadline.agents.nodes.error_handler_node.'
        'CreditsService.refund_credits'
    )
    is_system_error = mocker.patch(
        'threadline.agents.nodes.error_handler_node.'
        'ErrorClassifier.is_system_error',
        return_value=True,
    )

    state = {
        'id': '123',
        'credits_consumed': True,
        'credits_transaction_id': '456',
        'node_errors': {
            'llm_node': [
                {
                    'error_message': 'Request timeout',
                    'timestamp': '2026-05-22T00:00:00',
                }
            ]
        },
    }

    try:
        result = ErrorHandlerNode().execute_processing(state)
    finally:
        config.auto_refund_system_errors = original_auto_refund
        config.save(update_fields=['auto_refund_system_errors'])

    assert result is state
    assert result.get('credits_refunded') is None
    refund_credits.assert_not_called()
    is_system_error.assert_not_called()
