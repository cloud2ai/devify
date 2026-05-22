from __future__ import annotations

import pytest

from billing.models import Plan


@pytest.mark.django_db
def test_plan_save_preserves_explicit_admin_changes_on_update():
    plan = Plan.objects.create(
        name='Free',
        slug='free',
        description='Free plan',
        monthly_price_cents=0,
        metadata={'credits_per_period': 10, 'period_days': 30},
        status='active',
        is_active=True,
        is_internal=False,
        allow_self_purchase=False,
    )

    plan.is_active = False
    plan.allow_self_purchase = True
    plan.save()

    plan.refresh_from_db()
    assert plan.is_active is False
    assert plan.allow_self_purchase is True


@pytest.mark.django_db
def test_plan_save_derives_status_when_missing():
    plan = Plan.objects.create(
        name='Draft',
        slug='draft',
        description='Draft plan',
        monthly_price_cents=1000,
        metadata={'credits_per_period': 10, 'period_days': 30},
        status='',
        is_active=False,
        is_internal=False,
        allow_self_purchase=False,
    )

    assert plan.status == 'draft'


@pytest.mark.django_db
def test_plan_defaults_to_draft_status():
    plan = Plan(
        name='Draft Default',
        slug='draft-default',
        description='Default draft plan',
        monthly_price_cents=1000,
        metadata={'credits_per_period': 10, 'period_days': 30},
        is_active=False,
        is_internal=False,
        allow_self_purchase=False,
    )

    assert plan.status == 'draft'
