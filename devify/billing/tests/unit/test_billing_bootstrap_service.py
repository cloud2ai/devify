import yaml
import pytest

from billing.models import PaymentProvider, Plan
from billing.services.billing_bootstrap_service import bootstrap_local_billing


@pytest.mark.django_db
def test_bootstrap_local_billing_creates_providers_and_plans(
    tmp_path,
    mocker,
):
    plans_file = tmp_path / 'plans.yaml'
    plans_file.write_text(
        yaml.safe_dump(
            {
                'plans': [
                    {
                        'name': 'Starter',
                        'slug': 'starter',
                        'description': 'Starter plan',
                        'monthly_price_cents': 999,
                        'status': 'active',
                        'is_internal': False,
                        'allow_self_purchase': True,
                        'metadata': {
                            'credits_per_period': 100,
                            'period_days': 30,
                            'workflow_cost_credits': 1,
                        },
                    }
                ]
            }
        ),
        encoding='utf-8',
    )
    call_command = mocker.patch(
        'billing.services.billing_bootstrap_service.call_command'
    )

    result = bootstrap_local_billing(
        config_path=str(plans_file),
        initialize_credits=True,
    )

    assert result['plans_count'] == 1
    assert result['credits_initialized'] is True
    assert PaymentProvider.objects.filter(name='platform').exists()
    assert PaymentProvider.objects.filter(name='stripe').exists()
    assert Plan.objects.filter(slug='starter').exists()
    call_command.assert_called_once_with('init_user_credits')


@pytest.mark.django_db
def test_bootstrap_local_billing_can_skip_credits(
    tmp_path,
    mocker,
):
    plans_file = tmp_path / 'plans.yaml'
    plans_file.write_text(
        yaml.safe_dump({'plans': []}),
        encoding='utf-8',
    )
    call_command = mocker.patch(
        'billing.services.billing_bootstrap_service.call_command'
    )

    result = bootstrap_local_billing(
        config_path=str(plans_file),
        initialize_credits=False,
    )

    assert result['plans_count'] == 0
    assert result['credits_initialized'] is False
    call_command.assert_not_called()
