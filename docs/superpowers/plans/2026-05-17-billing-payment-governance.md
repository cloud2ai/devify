# Billing Payment Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split billing into system-level self-purchase controls and plan-level purchase semantics so platform grants, Stripe purchases, and future providers stay separable.

**Architecture:** Keep `Plan` as the source of entitlement data, add a small system config layer for global purchase controls, and make purchase eligibility a single explicit rule shared by backend and frontend. Preserve platform-granted subscriptions as the admin path and Stripe as the current self-purchase path, while keeping room for more providers later.

**Tech Stack:** Django, Django REST Framework, Vue 3, Vue I18n, PostgreSQL/SQLite JSONField support, pytest, Vite

---

### Task 1: Add system-level self-purchase controls

**Files:**
- Modify: `devify/billing/models.py`
- Modify: `devify/billing/migrations/0005_billingconfig.py` or create a new migration if 0005 is already applied in target branches
- Modify: `devify/billing/services/config_service.py`
- Modify: `devify/billing/admin_views.py`
- Modify: `ui/src/admin/pages/Billing/Settings.vue`
- Modify: `ui/src/admin/api/billing.js`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`
- Test: `devify/billing/tests/unit/test_config_service.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Extend the singleton billing config**

```python
class BillingConfig(models.Model):
    ...
    self_purchase_enabled = models.BooleanField(default=False)
    enabled_providers = models.JSONField(default=list)
```

- [ ] **Step 2: Expose the new fields in config serialization**

```python
def serialize_billing_config(config=None):
    return {
        ...
        'self_purchase_enabled': config.self_purchase_enabled,
        'enabled_providers': config.enabled_providers,
        'stripe_configured': stripe_configured,
        'recharge_enabled': (
            config.self_purchase_enabled
            and stripe_configured
            and 'stripe' in config.enabled_providers
        ),
    }
```

- [ ] **Step 3: Update the admin config editor to read and write the new fields**

```vue
<input type="checkbox" v-model="form.self_purchase_enabled" />
<input type="text" v-model="enabledProvidersText" placeholder="stripe" />
```

```js
const enabledProvidersText = computed({
  get: () => form.enabled_providers.join(','),
  set: (value) => {
    form.enabled_providers = value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  },
})
```

- [ ] **Step 4: Add backend coverage for the new config contract**

```python
def test_public_billing_status_includes_self_purchase_flags(db):
    status = get_public_billing_status()
    assert 'self_purchase_enabled' in status
    assert 'enabled_providers' in status
```

- [ ] **Step 5: Verify the admin config API persists the fields**

Run:

```bash
pytest devify/billing/tests/unit/test_config_service.py devify/billing/tests/integration/test_admin_billing_api.py -q
```

Expected: the new fields round-trip through the admin API and public billing status.

---

### Task 2: Split plan semantics into status, visibility, and self-purchase

**Files:**
- Modify: `devify/billing/models.py`
- Modify: `devify/billing/migrations/0004_add_is_internal_to_plan.py` or create a new migration for plan semantics
- Modify: `devify/billing/admin_views.py`
- Modify: `devify/billing/viewsets.py`
- Modify: `devify/billing/serializers.py`
- Modify: `devify/conf/billing/plans.yaml`
- Modify: `ui/src/admin/pages/Billing/Plans.vue`
- Modify: `ui/src/components/billing/SubscriptionPlans.vue`
- Modify: `ui/src/components/billing/CurrentSubscription.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`
- Test: `devify/billing/tests/integration/test_subscription_service.py`

- [ ] **Step 1: Add explicit plan fields and keep backwards compatibility for one release**

```python
class Plan(models.Model):
    status = models.CharField(
        max_length=16,
        default='draft',
        choices=[
            ('draft', 'Draft'),
            ('active', 'Active'),
        ],
    )
    is_internal = models.BooleanField(default=False)
    allow_self_purchase = models.BooleanField(default=False)
```

Keep `is_active` only as a temporary compatibility alias if needed for migration, then remove it in the cleanup task below.

- [ ] **Step 2: Migrate existing plan data from the current three-state UI model**

```python
migration_map = {
    'public_paid': {
        'status': 'active',
        'is_internal': False,
        'allow_self_purchase': True,
    },
    'platform_private': {
        'status': 'active',
        'is_internal': True,
        'allow_self_purchase': False,
    },
    'draft': {
        'status': 'draft',
        'is_internal': False,
        'allow_self_purchase': False,
    },
}
```

- [ ] **Step 3: Update the admin plan editor to save the new explicit fields**

```js
const canUserSee = plan.status === 'active' && !plan.is_internal
const canUserBuy =
  plan.status === 'active' &&
  plan.allow_self_purchase &&
  !plan.is_internal
```

- [ ] **Step 4: Update the public plan query to use the new semantics**

```python
Plan.objects.filter(status='active', is_internal=False)
```

- [ ] **Step 5: Update frontend purchase affordances to use the new semantics**

```ts
const canPurchase = computed(() =>
  props.plan.status === 'active' &&
  props.plan.allow_self_purchase &&
  !props.plan.is_internal &&
  billingStatus.value.self_purchase_enabled &&
  billingStatus.value.enabled_providers.includes('stripe') &&
  !!planPrice
)
```

- [ ] **Step 6: Verify the public billing page hides internal plans and still shows public buyable ones**

Run:

```bash
cd ui && npm run build
```

Expected: build passes and the plan cards still render, but only for active non-internal plans.

---

### Task 3: Make purchase eligibility a single backend rule

**Files:**
- Modify: `devify/billing/services/payment_provider_gateway.py`
- Modify: `devify/billing/viewsets.py`
- Modify: `devify/billing/admin_views.py`
- Modify: `devify/billing/serializers.py`
- Modify: `devify/billing/models.py`
- Test: `devify/billing/tests/unit/test_payment_provider_gateway.py`
- Test: `devify/billing/tests/integration/test_webhooks.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Introduce a shared helper that decides if a user can self-purchase a plan**

```python
def can_user_purchase(plan, provider_name, billing_status) -> bool:
    return (
        plan.status == 'active'
        and plan.allow_self_purchase
        and not plan.is_internal
        and billing_status['self_purchase_enabled']
        and provider_name in billing_status['enabled_providers']
        and PlanPrice.objects.filter(
            plan=plan,
            provider__name=provider_name,
            is_active=True,
        ).exists()
    )
```

- [ ] **Step 2: Use the helper in the checkout endpoint and hide invalid payment paths early**

```python
gateway = get_billing_gateway('stripe')
if not can_user_purchase(plan, 'stripe', get_public_billing_status()):
    return Response({'detail': 'Purchase is not available.'}, status=400)
```

- [ ] **Step 3: Preserve platform assignment as an admin-only path**

```python
subscription = SubscriptionService.switch_plan_for_user(user, plan, provider_name='platform')
```

- [ ] **Step 4: Add tests for each eligibility branch**

```python
def test_can_user_purchase_requires_active_public_plan():
    ...

def test_can_user_purchase_requires_enabled_provider():
    ...

def test_can_user_purchase_requires_plan_price():
    ...
```

- [ ] **Step 5: Verify checkout still works for Stripe and fails fast otherwise**

Run:

```bash
pytest devify/billing/tests/unit/test_payment_provider_gateway.py devify/billing/tests/integration/test_webhooks.py -q
```

Expected: Stripe checkout still works, invalid provider/plan combinations are rejected.

---

### Task 4: Keep admin plan assignment on platform and make it explicit in UI copy

**Files:**
- Modify: `devify/billing/admin_views.py`
- Modify: `ui/src/admin/pages/Billing/components/BillingUserPlanPanel.vue`
- Modify: `ui/src/admin/pages/Billing/Index.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

- [ ] **Step 1: Keep the backend assignment endpoint platform-only**

```python
subscription = SubscriptionService.switch_plan_for_user(user, plan, provider_name='platform')
```

- [ ] **Step 2: Make the modal copy say this is a platform-granted action, not a purchase action**

```vue
<p class="mt-1 text-sm text-gray-500">
  {{ t('billing.users.assignPlanHint') }}
</p>
```

Suggested copy:

```json
"billing.users.assignPlanHint": "This action assigns the selected plan through the platform. It does not charge the user."
```

- [ ] **Step 3: Ensure the assign-plan UI does not expose provider selection for admins**

Keep the current selector focused on `plan`, not on `stripe` vs `platform`.

- [ ] **Step 4: Verify admin assignment stays independent from self-purchase config**

Run:

```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -q
```

Expected: plan assignment works even when `self_purchase_enabled` is false.

---

### Task 5: Clean up old compatibility naming after the new model ships

**Files:**
- Modify: `devify/billing/models.py`
- Modify: `devify/billing/services/config_service.py`
- Modify: `devify/billing/admin_views.py`
- Modify: `ui/src/admin/pages/Billing/Plans.vue`
- Modify: `ui/src/components/billing/SubscriptionPlans.vue`
- Modify: `ui/src/components/billing/CurrentSubscription.vue`
- Modify: `ui/src/admin/pages/Billing/Settings.vue`
- Modify: `devify/conf/billing/plans.yaml`

- [ ] **Step 1: Remove legacy `recharge_enabled` assumptions from business logic**

```python
# preferred
self_purchase_enabled = config.self_purchase_enabled
enabled_providers = config.enabled_providers
```

- [ ] **Step 2: Stop relying on the old `is_active + is_internal` three-state UI contract**

Use:

```python
status
is_internal
allow_self_purchase
```

- [ ] **Step 3: Remove temporary compatibility comments and stale labels**

This is the cleanup pass after the migration lands and the admin UI is updated.

- [ ] **Step 4: Run the full billing test slice and frontend build**

Run:

```bash
pytest devify/billing/tests -q
cd ui && npm run build
```

Expected: both pass before merge.

---

## Self-Review

### Spec coverage
- System-level self-purchase controls: covered by Task 1
- Plan field split: covered by Task 2
- PlanPrice purchase rule: covered by Task 3
- Admin platform assignment unchanged: covered by Task 4
- Data migration: covered by Task 2
- Cleanup of old naming: covered by Task 5

### Gaps
- This plan intentionally does not add a multi-provider chooser page yet; it keeps the current default direct-to-Stripe behavior and only adds the control plane needed for future expansion.
- This plan does not add a separate public system-config UI outside billing settings; it keeps the new control fields in the existing billing admin settings page.

