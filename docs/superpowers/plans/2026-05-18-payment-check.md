# Payment Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral Payment Check flow that can compare and safely recover payment-driven subscription state across providers, starting with Stripe, with both manual admin action and scheduled task support.

**Architecture:** Keep one orchestration layer for Payment Check and small provider-specific checkers behind it. The manual admin action and the scheduled task both call the same service, while platform-assigned subscriptions remain out of scope. Store operator-visible settings in `BillingConfig`, update the Celery beat row when settings change, and record both task runs and per-user billing audits.

**Tech Stack:** Django, Django REST Framework, djstripe, Celery beat, Vue 3, Vite, `django_celery_beat`, pytest, Vue i18n.

---

### Task 1: Add BillingConfig fields and settings UI for Payment Check

**Files:**
- Modify: `devify/billing/models.py`
- Create: `devify/billing/migrations/0010_billingconfig_payment_check_fields.py`
- Modify: `devify/billing/services/config_service.py`
- Modify: `devify/billing/admin_views.py`
- Modify: `ui/src/admin/pages/Billing/Settings.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`
- Test: `devify/billing/tests/unit/test_config_service.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_serialize_and_update_billing_config_payment_check_fields(db):
    config = get_billing_config()
    config.payment_check_enabled = True
    config.payment_check_providers = ['stripe']
    config.payment_check_schedule = '0 3 * * *'
    config.save()

    data = serialize_billing_config(config)
    assert data['payment_check_enabled'] is True
    assert data['payment_check_providers'] == ['stripe']
    assert data['payment_check_schedule'] == '0 3 * * *'

    updated = update_billing_config(
        config,
        {
            'payment_check_enabled': False,
            'payment_check_providers': ['stripe'],
            'payment_check_schedule': '30 2 * * *',
        },
    )
    assert updated.payment_check_enabled is False
    assert updated.payment_check_providers == ['stripe']
    assert updated.payment_check_schedule == '30 2 * * *'
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest devify/billing/tests/unit/test_config_service.py -k payment_check -v
```

Expected: fail because the BillingConfig fields and serialization do not exist yet.

- [ ] **Step 3: Write minimal implementation**
  - Add `payment_check_enabled`, `payment_check_providers`, and `payment_check_schedule` to `BillingConfig`.
  - Default them to `False`, `[]`, and `''`.
  - Extend `serialize_billing_config()` and `update_billing_config()` to round-trip these fields.
  - Expose the fields in `BillingAdminConfigAPIView`.
  - Add a new settings card in `ui/src/admin/pages/Billing/Settings.vue` under the existing config page sections.
  - Add labels, placeholders, and helper copy in both locale files.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest devify/billing/tests/unit/test_config_service.py -k payment_check -v
pytest devify/billing/tests/integration/test_admin_billing_api.py -k config -v
cd ui && npm run build
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add devify/billing/models.py devify/billing/migrations/0010_billingconfig_payment_check_fields.py devify/billing/services/config_service.py devify/billing/admin_views.py ui/src/admin/pages/Billing/Settings.vue ui/src/admin/locales/zh-CN.json ui/src/admin/locales/en.json devify/billing/tests/unit/test_config_service.py devify/billing/tests/integration/test_admin_billing_api.py
git commit -m "Add payment check config controls"
```

### Task 2: Build the provider-neutral Payment Check service and Stripe checker

**Files:**
- Create: `devify/billing/services/payment_check/__init__.py`
- Create: `devify/billing/services/payment_check/base.py`
- Create: `devify/billing/services/payment_check/registry.py`
- Create: `devify/billing/services/payment_check/stripe.py`
- Create: `devify/billing/services/payment_check/service.py`
- Modify: `devify/billing/services/subscription_service.py`
- Modify: `devify/billing/services/payment_provider_gateway.py` if needed for shared helpers only
- Test: `devify/billing/tests/unit/test_payment_check_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_payment_check_stripe_checker_reports_safe_missing_subscription(
    mocker,
    test_user,
):
    user = test_user
    checker = StripePaymentChecker()

    mocker.patch.object(checker, 'list_remote_subscriptions', return_value=[
        {'id': 'sub_123', 'status': 'active', 'customer': 'cus_123'}
    ])
    mocker.patch.object(checker, 'build_local_match_key', return_value=('stripe', 'sub_123'))

    result = checker.check_user(user, mode='report_only')

    assert result['provider'] == 'stripe'
    assert result['differences']
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest devify/billing/tests/unit/test_payment_check_service.py -v
```

Expected: fail because the payment check package does not exist yet.

- [ ] **Step 3: Write minimal implementation**
  - Add a small `PaymentCheckProvider` interface with `is_configured()`, `list_remote_subscriptions()`, `build_local_match_key()`, `compare_local_and_remote()`, and `repair_local_state()`.
  - Implement Stripe first, using `djstripe.Customer` and the Stripe subscription list as the remote source.
  - Reuse `SubscriptionService.sync_from_djstripe()` for safe recovery when Stripe is clearly ahead of local state.
  - Keep `platform` subscriptions out of the provider scan.
  - Return a structured result with provider name, scanned count, difference list, repaired count, and failures.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest devify/billing/tests/unit/test_payment_check_service.py -v
pytest devify/billing/tests/unit/test_stripe_sync_service.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add devify/billing/services/payment_check devify/billing/services/subscription_service.py devify/billing/tests/unit/test_payment_check_service.py
git commit -m "Add provider-neutral payment check service"
```

### Task 3: Add the manual Payment Check admin action and user-subscription-page entry

**Files:**
- Modify: `devify/billing/admin_views.py`
- Modify: `devify/billing/admin_urls.py`
- Modify: `ui/src/admin/api/billing.js`
- Modify: `ui/src/admin/pages/Billing/Index.vue`
- Modify: `ui/src/admin/pages/Billing/components/BillingUserDrawer.vue`
- Create: `ui/src/admin/pages/Billing/components/BillingPaymentCheckDialog.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Write the failing test**

```python
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def test_admin_can_run_payment_check_for_stripe(mocker, test_user):
    User = get_user_model()
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='pass12345',
    )
    mocker.patch(
        'billing.admin_views.PaymentCheckService.run',
        return_value={
            'provider': 'stripe',
            'differences': [],
            'repaired_count': 1,
            'failed_count': 0,
        },
    )

    client = APIClient()
    client.force_authenticate(admin)
    response = client.post(
        '/api/v1/admin/billing/payment-check',
        {'providers': ['stripe'], 'mode': 'report_only'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['provider_runs'][0]['provider'] == 'stripe'
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -k payment_check -v
```

Expected: fail because the admin endpoint and frontend action do not exist yet.

- [ ] **Step 3: Write minimal implementation**
  - Add a provider-neutral admin endpoint that accepts `providers` and `mode`.
  - Load provider options from `BillingConfig.payment_check_providers`.
  - Add a top-level `核对支付状态` / `Payment Check` button on the user subscription page header.
  - Create a small dialog that lets the admin choose provider(s) and check mode.
  - Return a short summary and use the existing toast pattern for success/failure.
  - Keep the existing user-level `从 Stripe 同步` recovery button unchanged for now.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -k payment_check -v
cd ui && npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add devify/billing/admin_views.py devify/billing/admin_urls.py ui/src/admin/api/billing.js ui/src/admin/pages/Billing/Index.vue ui/src/admin/pages/Billing/components/BillingUserDrawer.vue ui/src/admin/pages/Billing/components/BillingPaymentCheckDialog.vue ui/src/admin/locales/zh-CN.json ui/src/admin/locales/en.json devify/billing/tests/integration/test_admin_billing_api.py
git commit -m "Add manual payment check admin flow"
```

### Task 4: Add the scheduled Payment Check task and config-driven beat sync

**Files:**
- Modify: `devify/billing/tasks.py`
- Modify: `devify/billing/periodic_tasks.py`
- Create: `devify/billing/services/payment_check_scheduler.py`
- Modify: `devify/billing/admin_views.py`
- Test: `devify/billing/tests/unit/test_payment_check_scheduler.py`
- Test: `devify/billing/tests/integration/test_billing_automation.py`

- [ ] **Step 1: Write the failing test**

```python
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def test_sync_payment_check_task_updates_periodic_task(mocker):
    User = get_user_model()
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='pass12345',
    )
    client = APIClient()
    client.force_authenticate(admin_user)
    sync_periodic_task = mocker.patch(
        'billing.services.payment_check_scheduler.sync_payment_check_periodic_task'
    )

    response = client.put(
        '/api/v1/admin/billing/config',
        {
            'payment_check_enabled': True,
            'payment_check_providers': ['stripe'],
            'payment_check_schedule': '30 2 * * *',
        },
        format='json',
    )

    assert response.status_code == 200
    sync_periodic_task.assert_called_once()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest devify/billing/tests/unit/test_payment_check_scheduler.py -v
```

Expected: fail because the scheduler helper does not exist yet.

- [ ] **Step 3: Write minimal implementation**
  - Add a `Payment Check` periodic task that calls the same provider-neutral service as the manual action.
  - Read the provider list and schedule from `BillingConfig`.
  - Add a helper that upserts the `django_celery_beat` row when config changes.
  - Keep the task name provider-neutral, not Stripe-specific.
  - Record run metadata with the existing `TaskTracer`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest devify/billing/tests/unit/test_payment_check_scheduler.py -v
pytest devify/billing/tests/integration/test_billing_automation.py -k payment_check -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add devify/billing/tasks.py devify/billing/periodic_tasks.py devify/billing/services/payment_check_scheduler.py devify/billing/admin_views.py devify/billing/tests/unit/test_payment_check_scheduler.py devify/billing/tests/integration/test_billing_automation.py
git commit -m "Add scheduled payment check support"
```

### Task 5: Add end-to-end verification and keep coverage aligned

**Files:**
- Modify: `devify/billing/tests/TEST_SCENARIOS.md`
- Modify: `devify/billing/tests/integration/test_webhooks.py`
- Modify: `devify/billing/tests/integration/test_subscription_service.py`
- Modify: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Write the failing test**

```python
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def test_manual_payment_check_skips_platform_subscriptions(
    mocker,
    test_user_with_free_subscription,
):
    User = get_user_model()
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='pass12345',
    )

    mocker.patch('billing.admin_views.PaymentCheckService.run')

    client = APIClient()
    client.force_authenticate(admin)
    response = client.post(
        '/api/v1/admin/billing/payment-check',
        {'providers': ['stripe'], 'mode': 'auto_fix_safe'},
        format='json',
    )

    assert response.status_code == 200
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -k payment_check -v
```

Expected: fail until the provider-neutral check service and platform skip logic are complete.

- [ ] **Step 3: Write minimal implementation**
  - Add coverage for platform skip behavior.
  - Add coverage for safe auto-fix cases and report-only cases.
  - Update `TEST_SCENARIOS.md` with the new manual and scheduled payment-check paths.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest devify/billing/tests/unit/test_payment_check_service.py \
       devify/billing/tests/unit/test_payment_check_scheduler.py \
       devify/billing/tests/integration/test_admin_billing_api.py \
       devify/billing/tests/integration/test_billing_automation.py -v
cd ui && npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add devify/billing/tests/TEST_SCENARIOS.md devify/billing/tests/integration/test_webhooks.py devify/billing/tests/integration/test_subscription_service.py devify/billing/tests/integration/test_admin_billing_api.py
git commit -m "Expand payment check coverage"
```

## Review Notes
- The plan keeps `Payment Check` provider-neutral in naming and structure.
- It uses the existing `TaskTracer` and billing audit log instead of adding a new tracking system.
- It keeps the current Stripe-only reality but leaves the provider interface open for future checkers.
- It does not auto-run checks on page load.
- It avoids touching the existing user-level `从 Stripe 同步` recovery path except where shared code is useful.
