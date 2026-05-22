# Billing Bootstrap and Stripe Sync Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep local billing bootstrap in startup, move Stripe product/price sync to explicit manual/admin actions, and keep runtime Stripe settings database-driven.

**Architecture:** Treat `BillingConfig` as the runtime source of truth. Environment variables only seed defaults when the config row is first created. Split the current monolithic billing initialization into: local bootstrap for plans/provider/credits, and Stripe sync for products/prices. Startup should call only the local bootstrap path. Admins should be able to sync a single plan to Stripe from the management console without relying on the bootstrap command.

**Tech Stack:** Django, Django REST Framework, Stripe SDK, Vue 3, Vite, pytest, bash.

---

### Task 1: Split startup bootstrap from Stripe sync

**Files:**
- Create: `devify/billing/services/billing_bootstrap_service.py`
- Create: `devify/billing/management/commands/init_billing_base.py`
- Modify: `devify/billing/management/commands/init_billing_stripe.py`
- Modify: `docker/entrypoint.sh`
- Test: `devify/billing/tests/unit/test_billing_bootstrap_service.py`

**What this task does**
- Extract the non-Stripe parts of billing initialization into a reusable bootstrap service.
- Make the startup path call only local bootstrap:
  - billing config defaults
  - payment provider rows
  - plans
  - user credits
- Keep `init_billing_stripe` as a manual-only repair/sync command for Stripe setup, not a startup dependency.

- [ ] **Step 1: Write the failing tests**

```python
def test_bootstrap_local_billing_creates_base_records(mocker):
    mocker.patch("billing.services.billing_bootstrap_service.Plan.objects")
    mocker.patch("billing.services.billing_bootstrap_service.PaymentProvider.objects")
    mocker.patch("billing.services.billing_bootstrap_service.call_command")

    result = bootstrap_local_billing()

    assert result is True


def test_bootstrap_local_billing_does_not_touch_stripe_sdk(mocker):
    stripe_create = mocker.patch(
        "billing.services.billing_bootstrap_service.stripe"
    )

    bootstrap_local_billing()

    assert not stripe_create.Product.create.called
    assert not stripe_create.Price.create.called
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest devify/billing/tests/unit/test_billing_bootstrap_service.py -q
```

Expected: fail because the bootstrap service does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
def bootstrap_local_billing() -> bool:
    get_billing_config()
    ensure_payment_provider("platform", "Platform assignment")
    ensure_payment_provider("stripe", "Stripe")
    ensure_plans_from_yaml()
    call_command("init_user_credits")
    return True
```

`init_billing_base.py` should call only `bootstrap_local_billing()`.

`init_billing_stripe.py` should be reduced to Stripe setup only:
- keep it as a manual operator command
- keep product/price sync and webhook repair there if still needed
- remove any dependency from startup

`docker/entrypoint.sh` should call only the base command:

```bash
python manage.py init_billing_base || log "Billing base initialization completed with warnings"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest devify/billing/tests/unit/test_billing_bootstrap_service.py -q
```

Expected: pass.

- [ ] **Step 5: Verify startup no longer depends on Stripe sync**

Search and update any startup references so they point to the base command instead of the Stripe command:

```bash
rg -n "init_billing_stripe" docker devify | sed -n '1,200p'
```

Expected: startup references should point to `init_billing_base`.

---

### Task 2: Add a reusable Stripe plan sync service and admin endpoint

**Files:**
- Create: `devify/billing/services/stripe_sync_service.py`
- Modify: `devify/billing/management/commands/init_billing_stripe.py`
- Modify: `devify/billing/admin_views.py`
- Modify: `devify/billing/admin_urls.py`
- Test: `devify/billing/tests/unit/test_stripe_sync_service.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

**What this task does**
- Move current Stripe product/price creation logic into a reusable service that can sync one plan or a list of plans.
- Add a manager-facing endpoint to sync one plan at a time:

```http
POST /api/v1/admin/billing/plans/{plan_id}/sync-stripe
```

- Keep the current plan payload shape and return refreshed Stripe mapping fields:
  - `stripe_price_id`
  - `stripe_product_id`

- [ ] **Step 1: Write the failing unit tests**

```python
def test_sync_plan_to_stripe_creates_price_for_public_plan(mocker, public_plan):
    mocker.patch("billing.services.stripe_sync_service.stripe.Product.create")
    mocker.patch("billing.services.stripe_sync_service.stripe.Price.create")

    plan_price = sync_plan_to_stripe(public_plan)

    assert plan_price.provider.name == "stripe"
    assert plan_price.provider_price_id
    assert plan_price.provider_product_id


def test_sync_plan_to_stripe_rejects_internal_plan(internal_plan):
    with pytest.raises(ValueError, match="not eligible for Stripe sync"):
        sync_plan_to_stripe(internal_plan)
```

- [ ] **Step 2: Run the unit test to verify it fails**

Run:

```bash
pytest devify/billing/tests/unit/test_stripe_sync_service.py -q
```

Expected: fail because the service does not exist yet.

- [ ] **Step 3: Implement the minimal sync service**

```python
def sync_plan_to_stripe(plan: Plan) -> PlanPrice:
    if (
        plan.status != Plan.STATUS_ACTIVE
        or plan.is_internal
        or not plan.allow_self_purchase
    ):
        raise ValueError("Plan is not eligible for Stripe sync")

    product_id = ensure_unified_product()
    stripe_price = stripe.Price.create(...)

    payment_provider = PaymentProvider.objects.get(name="stripe")
    plan_price, _ = PlanPrice.objects.update_or_create(
        plan=plan,
        provider=payment_provider,
        defaults={
            "provider_product_id": product_id,
            "provider_price_id": stripe_price.id,
            "interval": "month",
            "is_active": True,
        },
    )
    return plan_price
```

The service should also expose:

```python
def sync_public_plans_to_stripe(plans: Iterable[Plan]) -> list[PlanPrice]:
    return [sync_plan_to_stripe(plan) for plan in plans]
```

The admin endpoint should:
- load the plan by id
- reject draft/internal/non-self-purchasable plans
- call `sync_plan_to_stripe(plan)`
- write a billing audit log entry with `action_type='plan.stripe_sync'`
- return the refreshed plan payload

Suggested endpoint shape in `admin_views.py`:

```python
class BillingAdminPlanSyncStripeAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, plan_id):
        plan = get_object_or_404(Plan, pk=plan_id)
        plan_price = sync_plan_to_stripe(plan)
        queue_billing_audit_event(
            action_type="plan.stripe_sync",
            source="admin_api",
            actor_id=request.user.id,
            actor_name=request.user.username,
            resource_type="plan",
            resource_id=plan.id,
            after_data=_plan_with_stripe_data(plan),
            context={
                "plan_id": plan.id,
                "plan_slug": plan.slug,
                "stripe_price_id": plan_price.provider_price_id,
            },
        )
        return Response(_plan_with_stripe_data(plan))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest devify/billing/tests/unit/test_stripe_sync_service.py devify/billing/tests/integration/test_admin_billing_api.py -q
```

Expected: pass.

- [ ] **Step 5: Keep `init_billing_stripe` as a manual repair command**

Update `init_billing_stripe.py` so it becomes an explicit operator tool for Stripe repair/backfill, not a startup dependency. Keep its help text and CLI behavior aligned with manual use.

---

### Task 3: Add a small Stripe sync affordance in the admin plans page

**Files:**
- Modify: `ui/src/admin/api/billing.js`
- Modify: `ui/src/admin/pages/Billing/Plans.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`

**What this task does**
- Add a single row action to sync one plan to Stripe.
- Show whether a plan is already synced by reusing `plan.stripe_price_id`.
- Keep the existing table layout and horizontal scrolling; do not switch the page to cards.

- [ ] **Step 1: Write the failing frontend expectation**

Add a new API method:

```javascript
syncPlanToStripe(planId) {
  return apiClient
    .post(`/v1/admin/billing/plans/${planId}/sync-stripe`)
    .then(extractData)
}
```

And wire it into the existing plans table row actions.

- [ ] **Step 2: Run the frontend build to verify it fails before wiring exists**

Run:

```bash
cd ui && npm run build
```

Expected: fail before the new API method/button wiring exists.

- [ ] **Step 3: Implement the UI**

Add one small button in the actions column:

```vue
<BaseButton
  variant="outline"
  size="sm"
  :loading="syncingStripePlanId === plan.id"
  @click="syncStripe(plan)"
>
  {{ plan.stripe_price_id ? t('billing.plans.resyncStripe') : t('billing.plans.syncStripe') }}
</BaseButton>
```

The handler should:
- call the new admin API
- refresh the plans list on success
- show an error toast on failure

Add translations for:
- `billing.plans.syncStripe`
- `billing.plans.resyncStripe`
- `billing.plans.stripeSynced`
- `billing.plans.stripeNotSynced`

- [ ] **Step 4: Run the frontend build again**

Run:

```bash
cd ui && npm run build
```

Expected: pass.

- [ ] **Step 5: Keep the UI minimal**

Do not add a separate Stripe sync page yet.
The goal is only to make syncing discoverable from the existing plans list.

---

### Task 4: Verify runtime config and docs stay consistent

**Files:**
- Modify: `devify/core/settings/billing.py` only if comments or startup assumptions need cleanup
- Modify: `README.md` or deployment docs if they mention the old startup behavior
- Test: `devify/billing/tests/unit/test_config_service.py`

**What this task does**
- Make sure the plan matches the actual config flow:
  - environment variables seed the DB once
  - `BillingConfig` is the runtime source of truth
  - startup no longer depends on Stripe sync
- Clean up any stale docs or comments that still say Stripe is initialized automatically at boot.

- [ ] **Step 1: Run the config tests**

Run:

```bash
pytest devify/billing/tests/unit/test_config_service.py -q
```

Expected: pass.

- [ ] **Step 2: Run the frontend build**

Run:

```bash
cd ui && npm run build
```

Expected: pass.

- [ ] **Step 3: Update docs if any startup docs still mention automatic Stripe sync**

Search:

```bash
rg -n "init_billing_stripe|Stripe sync|startup" README.md docker devify | sed -n '1,200p'
```

Expected: any startup instructions should refer to the base bootstrap command, not automatic Stripe sync.

---

## Self-review

### Spec coverage
- Startup bootstrap and Stripe sync are now separate concerns.
- Local billing setup still runs at startup.
- Stripe sync becomes an explicit manual/admin action.
- Runtime Stripe settings remain database-driven.
- The frontend gets only a minimal sync affordance, not a large redesign.

### Placeholder scan
- No TODO/TBD placeholders remain.
- Each task has files, tests, commands, and concrete implementation snippets.

### Type consistency
- `bootstrap_local_billing()` handles local-only initialization.
- `sync_plan_to_stripe(plan)` handles one-plan Stripe syncing.
- `BillingAdminPlanSyncStripeAPIView` is the explicit admin endpoint for one plan.

## Open questions for review
- Should `init_billing_stripe` remain as a Stripe-only manual repair command, or should it be renamed to `sync_billing_stripe` for clarity?
- Do you want a bulk “sync all eligible plans” admin action, or is single-plan sync enough for now?
- Should the plans list show a separate sync status chip, or is the action button alone sufficient?

