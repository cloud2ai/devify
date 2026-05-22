# Stripe Sync Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit admin-facing Stripe sync action for plans, so Stripe prices are generated and retried from the management console instead of relying on the bootstrap command for day-to-day operations.

**Architecture:** Extract the current Stripe product/price creation logic into a reusable billing sync service. Keep `init_billing_stripe` as a bootstrap/repair command that calls the same service. Expose a narrow admin API that syncs one plan at a time and returns updated Stripe mapping fields. Keep the frontend simple: show sync status from `stripe_price_id` and add one sync action per plan row.

**Tech Stack:** Django, Django REST Framework, Stripe SDK, Vue 3, Vite, pytest, existing billing admin API.

---

### Task 1: Extract reusable Stripe plan sync service

**Files:**
- Create: `devify/billing/services/stripe_sync_service.py`
- Modify: `devify/billing/management/commands/init_billing_stripe.py`
- Test: `devify/billing/tests/unit/test_stripe_sync_service.py`

**What this task does**
- Move the current `create_stripe_products()` logic out of the management command into a reusable service.
- Make the service responsible for:
  - ensuring the shared Stripe product exists
  - creating/updating the Stripe price for one eligible plan
  - returning the local `PlanPrice` row that now points at Stripe
- Keep the command as a thin wrapper that calls the same service for all eligible plans.

- [ ] **Step 1: Write the failing tests**

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


def test_sync_public_plans_to_stripe_is_idempotent(mocker, public_plan):
    mocker.patch("billing.services.stripe_sync_service.stripe.Product.create")
    mocker.patch("billing.services.stripe_sync_service.stripe.Price.create")

    first = sync_plan_to_stripe(public_plan)
    second = sync_plan_to_stripe(public_plan)

    assert first.id == second.id
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest devify/billing/tests/unit/test_stripe_sync_service.py -q
```

Expected: fail because `stripe_sync_service.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
def sync_plan_to_stripe(plan: Plan) -> PlanPrice:
    if plan.status != Plan.STATUS_ACTIVE or plan.is_internal or not plan.allow_self_purchase:
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

The service should also expose a bulk helper used by the bootstrap command:

```python
def sync_public_plans_to_stripe(plans: Iterable[Plan]) -> list[PlanPrice]:
    return [sync_plan_to_stripe(plan) for plan in plans]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest devify/billing/tests/unit/test_stripe_sync_service.py -q
```

Expected: pass.

- [ ] **Step 5: Keep the bootstrap command as a thin wrapper**

Update `init_billing_stripe.py` so the Stripe branch calls the reusable service instead of embedding the product/price creation loop inline. The command should still be used for:
- fresh installs
- repair runs
- backfilling missing Stripe data

---

### Task 2: Add an admin endpoint to sync one plan to Stripe

**Files:**
- Modify: `devify/billing/admin_views.py`
- Modify: `devify/billing/admin_urls.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`

**What this task does**
- Add a manager-facing endpoint for one plan at a time:

```http
POST /api/v1/admin/billing/plans/{plan_id}/sync-stripe
```

- The endpoint should:
  - require admin permission
  - refuse draft/internal/non-self-purchasable plans
  - call `sync_plan_to_stripe(plan)`
  - write a billing audit log entry with `action_type='plan.stripe_sync'`
  - return the refreshed plan payload with `stripe_price_id` / `stripe_product_id`

- [ ] **Step 1: Write the failing integration tests**

```python
def test_admin_can_sync_public_plan_to_stripe(admin_client, public_plan):
    response = admin_client.post(f"/api/v1/admin/billing/plans/{public_plan.id}/sync-stripe")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["stripe_price_id"]
    assert payload["stripe_product_id"]


def test_admin_cannot_sync_internal_plan_to_stripe(admin_client, internal_plan):
    response = admin_client.post(f"/api/v1/admin/billing/plans/{internal_plan.id}/sync-stripe")
    assert response.status_code == 400
    assert "not eligible" in response.json()["error"].lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -q -k "sync_public_plan_to_stripe or sync_internal_plan_to_stripe"
```

Expected: fail because the route and handler do not exist yet.

- [ ] **Step 3: Implement the endpoint**

Add a small APIView in `admin_views.py` and wire it explicitly in `admin_urls.py`:

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
            target_user_id=None,
            target_username="",
            resource_type="plan",
            resource_id=plan.id,
            before_data={},
            after_data=_plan_with_stripe_data(plan),
            context={
                "plan_id": plan.id,
                "plan_slug": plan.slug,
                "stripe_price_id": plan_price.provider_price_id,
            },
        )
        return Response(_plan_with_stripe_data(plan))
```

And add the route explicitly:

```python
path(
    "plans/<int:plan_id>/sync-stripe",
    BillingAdminPlanSyncStripeAPIView.as_view(),
),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest devify/billing/tests/integration/test_admin_billing_api.py -q -k "sync_public_plan_to_stripe or sync_internal_plan_to_stripe"
```

Expected: pass.

- [ ] **Step 5: Keep the response shape consistent**

Make sure the endpoint returns the same plan payload shape already used by the plans list:
- `stripe_price_id`
- `stripe_product_id`
- `status`
- `is_internal`
- `allow_self_purchase`

That avoids adding a second plan DTO just for the sync button.

---

### Task 3: Add a Stripe sync action to the admin plans page

**Files:**
- Modify: `ui/src/admin/api/billing.js`
- Modify: `ui/src/admin/pages/Billing/Plans.vue`
- Modify: `ui/src/admin/locales/zh-CN.json`
- Modify: `ui/src/admin/locales/en.json`

**What this task does**
- Add a per-plan “同步 Stripe” / “重新同步 Stripe” action in the plans table.
- Show a simple sync state from existing fields:
  - if `plan.stripe_price_id` exists: `已同步`
  - else: `未同步`
- Keep the table layout intact; do not switch to cards or change the page structure.

- [ ] **Step 1: Write the failing frontend build expectation**

Add a new API method:

```javascript
syncPlanToStripe(planId) {
  return apiClient
    .post(`/v1/admin/billing/plans/${planId}/sync-stripe`)
    .then(extractData)
}
```

And use it from the table row action in `Plans.vue`.

- [ ] **Step 2: Run the frontend build to verify it fails before the code exists**

Run:

```bash
cd ui && npm run build
```

Expected: fail before the API method and button wiring are added.

- [ ] **Step 3: Implement the UI**

Add one small action button in the existing actions column:

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

The click handler should:
- call `billingAdminApi.syncPlanToStripe(plan.id)`
- refresh the plan list on success
- show an error toast on failure

Add translation keys for:
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

- [ ] **Step 5: Keep the page minimal**

Do not add a separate Stripe sync page or a new wizard yet.
The goal is a single explicit row action that makes Stripe sync discoverable without adding more surface area to the admin console.

---

### Task 4: Verify the bootstrap path still works

**Files:**
- Modify: `devify/billing/management/commands/init_billing_stripe.py`
- Test: `devify/billing/tests/integration/test_admin_billing_api.py`
- Test: `devify/billing/tests/unit/test_stripe_sync_service.py`

**What this task does**
- Confirm the bootstrap command still uses the same service and still handles:
  - fresh database initialization
  - Stripe credential absence
  - idempotent plan syncing
- This keeps the command useful as a repair/backfill tool, while making the admin console the normal operator path.

- [ ] **Step 1: Run the focused backend tests**

Run:

```bash
pytest devify/billing/tests/unit/test_stripe_sync_service.py devify/billing/tests/integration/test_admin_billing_api.py -q
```

Expected: pass.

- [ ] **Step 2: Run the frontend build**

Run:

```bash
cd ui && npm run build
```

Expected: pass.

- [ ] **Step 3: Confirm operational behavior**

Manual verification checklist:
- open the billing plans admin page
- sync one active public plan to Stripe
- refresh the list and confirm `stripe_price_id` is populated
- verify the user-facing billing page can now purchase that plan
- verify internal plans still cannot be synced or purchased

---

## Self-review

### Spec coverage
- The plan adds an explicit admin-side Stripe sync action.
- The plan keeps the bootstrap command but makes it a thin wrapper.
- The plan keeps the scope minimal: one provider (`stripe`) and one admin operation first.
- The plan includes backend tests and frontend build verification.

### Placeholder scan
- No `TBD`, `TODO`, or vague “implement later” steps remain.
- Every task lists exact files and exact commands.

### Type consistency
- The same plan sync entrypoint is used throughout:
  - `sync_plan_to_stripe(plan)`
  - `sync_public_plans_to_stripe(plans)`
- The admin API path is consistent:
  - `POST /api/v1/admin/billing/plans/{plan_id}/sync-stripe`
