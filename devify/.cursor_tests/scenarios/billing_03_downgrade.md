# Billing Scenario 3: Subscription Downgrade (Pro → Standard)

## Overview
Test the complete flow of downgrading from Pro Plan to Standard Plan.

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_downgrade_user`
- Password: `Test123456!`
- Initial Plan: Pro
- Initial Credits: 2000/2000
- Target Plan: Standard ($9.90/month)

---

## Test Steps

### Step 1: Prepare Test User

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_downgrade_user \
  --plan pro \
  --with-stripe \
  --cleanup-first
```

**Expected Output:**
```
✓ Created user: test_billing_downgrade_user
✓ Created Stripe customer: cus_xxx
✓ Attached test payment method: pm_xxx
✓ Created subscription: sub_xxx
✓ Synced to djstripe: sub_xxx
✓ Using Stripe period dates
✓ Plan: pro
✓ Status: active
✓ Auto-renew: true
✓ Stripe subscription ID: sub_xxx
```

---

### Step 2: Browser Test - Login and Downgrade

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_downgrade_user` / `Test123456!`
4. Click "Plan & Billing" in navigation
5. Verify Pro Plan displayed with 2000/2000 credits
6. Click "Downgrade to Standard Plan" button
7. Verify downgrade dialog appears

**Downgrade Dialog Verification:**
- ✅ Dialog title: "Downgrade Subscription"
- ✅ Message: "Are you sure you want to downgrade to Standard Plan?"
- ✅ Warning: "The downgrade will take effect at the end of current period"
- ✅ Shows period end date
- ✅ "Confirm Downgrade" button present
- ✅ "Cancel" button present

---

### Step 3: Confirm Downgrade

**Actions:**
1. Click "Confirm Downgrade" button
2. Wait for response (2-3 seconds)

**Expected Results:**
- ✅ Dialog closed
- ✅ Success message displayed (or no error)
- ✅ Plan still shows "Pro Plan" (unchanged during current period)
- ✅ Credits still show "2000 / 2000"
- ✅ Auto Renew remains "Yes"

**Important Note:**
Downgrade is scheduled in Stripe but won't take effect until:
- Current billing period ends, OR
- Stripe webhook `customer.subscription.updated` is triggered

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_downgrade_user \
  --expect-plan pro
```

**Expected Output:**
```
✓ Subscription verification passed
  Plan: pro (downgrade scheduled)
  Status: active
  Auto-renew: True
✓ Credits verification passed
  Base: 2000
  Available: 2000
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_downgrade_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Downgrade request successfully submitted to Stripe. Plan remains Pro until period end.
