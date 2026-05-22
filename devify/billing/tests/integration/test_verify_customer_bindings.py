from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from djstripe.models import Customer


@pytest.mark.django_db
def test_verify_customer_bindings_reports_unbound_customers(test_user):
    customer = Customer.objects.create(
        id='cus_unbound_1',
        subscriber=None,
        email='unbound@example.com',
        metadata={},
    )

    out = StringIO()
    call_command('verify_customer_bindings', stdout=out)

    output = out.getvalue()
    assert 'Unbound customers: 1' in output
    assert customer.id in output
    assert customer.email in output


@pytest.mark.django_db
def test_verify_customer_bindings_fails_when_requested(test_user):
    Customer.objects.create(
        id='cus_unbound_2',
        subscriber=None,
        email='unbound2@example.com',
        metadata={},
    )

    out = StringIO()

    with pytest.raises(CommandError):
        call_command(
            'verify_customer_bindings',
            '--fail-on-unbound',
            stdout=out,
        )
