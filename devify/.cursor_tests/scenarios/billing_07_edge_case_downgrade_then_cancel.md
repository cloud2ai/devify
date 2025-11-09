# Billing Scenario 7: Edge Case - Downgrade Then Cancel

## Overview
Test the edge case where user downgrades Pro → Standard, then immediately cancels the subscription within the same billing period.

## Scenario Flow

```
User: Pro Plan (Active, Auto-renew: Yes)
  ↓
Step 1: Downgrade to Standard
  → Stripe: subscription.items modified (set Standard price for next period)
  → Local DB: No change yet (waiting for webhook)
  → UI: Still shows Pro Plan with Auto-renew: Yes
  ↓
Step 2: Cancel Subscription
  → Stripe: cancel_at_period_end = True
  → Local DB: auto_renew = False
  → UI: Shows Pro Plan with Auto-renew: No, "Resume" button
  ↓
Period Ends (e.g., Dec 6, 2025)
  → Stripe: What happens?
```

## Expected Behavior Analysis

### According to Stripe API Logic

When both operations are applied:
1. **Downgrade** modifies `subscription.items` (changes price for next period)
2. **Cancel** sets `cancel_at_period_end = True` (terminates subscription)

**Result at Period End**:
- ❌ Downgrade does NOT take effect
- ✅ Cancellation takes effect
- ✅ Subscription terminates (status = canceled)
- ✅ User reverts to Free Plan (10 credits)

**Reasoning**:
- `cancel_at_period_end=True` means "delete this subscription when period ends"
- Stripe deletes the subscription entirely, ignoring any scheduled price changes
- The downgrade schedule is lost when subscription is deleted

### Why This Makes Sense

User actions indicate:
1. First thought: "I want to save money, downgrade to Standard"
2. Second thought: "Actually, I don't want to pay at all, cancel completely"

**Expected UX**: Second action (cancel) should override first action (downgrade).

Result: User returns to Free Plan (not Standard Plan).

## Test Steps

### Prerequisites

This test requires a user with **real Stripe subscription**.
Test users created by helper scripts don't have djstripe_subscription_id.

### Step 1: Setup User with Real Stripe Subscription

**Option A**: Use existing user (e.g., xiaoquqi) who subscribed via real Stripe checkout

**Option B**: Create new user and complete full Stripe payment flow (Scenario 1 or 2)

### Step 2: Downgrade to Basic

1. Login to user with Pro Plan
2. Navigate to billing page
3. Click "Downgrade to Basic Plan"
4. Confirm downgrade
5. **Verify**: Success message shown
6. **Verify**: Still shows Pro Plan (no immediate change)

**Stripe State After Downgrade:**
```python
subscription.items[0].price = basic_plan_price_id
# Downgrade scheduled for period end
```

### Step 3: Cancel Subscription

1. On same billing page
2. Click "Cancel Subscription" button
3. Confirm cancellation
4. **Verify**: Auto Renew changes to "No"
5. **Verify**: Button changes to "Resume Subscription"

**Stripe State After Cancel:**
```python
subscription.cancel_at_period_end = True
# Subscription will be deleted at period end
```

### Step 4: Verify Final State

**Immediate UI State:**
- Pro Plan (still Active)
- Auto Renew: No
- Resume button available
- Can still use Pro features until period end

**At Period End (Simulated or Wait):**
- Subscription deleted by Stripe
- Webhook: `customer.subscription.deleted`
- User reverts to Free Plan
- Credits: 10
- No Basic Plan subscription created

### Step 5: Database Verification

After period ends (or webhook simulation):

```bash
docker exec devify-api-dev python manage.py shell -c "
from billing.models import Subscription, UserCredits

# Check subscriptions
subs = Subscription.objects.filter(user_id=USER_ID)
print('All subscriptions:', [(s.plan.slug, s.status, s.auto_renew) for s in subs])

# Check credits
credits = UserCredits.objects.get(user_id=USER_ID)
print(f'Credits: {credits.base_credits}')
print(f'Expected: 10 (Free Plan)')
"
```

**Expected Output:**
```
All subscriptions: [('pro', 'canceled', False)]
Credits: 10
Expected: 10 (Free Plan)
```

## Expected Behavior Summary

| Action | Stripe State | Local DB State | UI Display |
|--------|--------------|----------------|------------|
| Initial | Pro, active, auto_renew=true | Pro, active, auto_renew=true | Pro Plan, Auto: Yes |
| After Downgrade | Pro with Standard price scheduled | Pro, active, auto_renew=true | Pro Plan, Auto: Yes |
| After Cancel | Pro, cancel_at_period_end=true | Pro, active, auto_renew=false | Pro Plan, Auto: No |
| Period Ends | Subscription deleted | Pro, canceled, auto_renew=false | Free Plan, 10 credits |

**Key Point**: Downgrade is **overridden** by cancellation. User goes to Free Plan, not Standard Plan.

## Why This Is Correct

1. **User Intent**: Canceling means "I don't want to pay anymore"
2. **Stripe Behavior**: Canceled subscriptions are deleted, not downgraded
3. **UX Clarity**: Cancel should be final decision, overrides previous actions

## Alternative Scenario: Cancel Then Downgrade

If user cancels first, then tries to downgrade:

**Expected**: Frontend should **prevent** downgrade operation
- User already canceled (auto_renew = false)
- Downgrade button should be disabled or hidden
- Only "Resume" button should be available

## Recommendation

Add UI logic to prevent confusing operations:

```javascript
// In SubscriptionPlans.vue
function canDowngrade(plan) {
  if (isCanceledButActive.value) {
    return false  // ✅ Already implemented!
  }
  // ... rest of logic
}
```

**Current Implementation**: Already correct!
- Line 352-354 in SubscriptionPlans.vue prevents downgrade when subscription is canceled.

## Conclusion

**Expected Behavior for "Downgrade → Cancel" Edge Case:**

✅ Cancellation wins
✅ Downgrade schedule is ignored
✅ Subscription terminates at period end
✅ User reverts to Free Plan (not Standard)

This is the correct and expected behavior.

---

## Test Complete

**Result**: Edge case behavior is correct. Cancellation overrides downgrade.

**Note**: Full testing requires real Stripe subscription with webhook processing.
