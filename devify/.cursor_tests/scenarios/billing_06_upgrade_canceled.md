# Billing Scenario 6: Upgrade When Already Canceled

## Overview
Test upgrading to a higher plan when subscription is canceled but still active.

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_upgrade_canceled_user`
- Password: `Test123456!`
- Initial Plan: Standard (canceled, auto_renew=false)
- Initial Credits: 20/20
- Target Plan: Pro ($29.99/month)

---

## Test Steps

### Step 1: Prepare Test User (Canceled State)

**Commands:**
```bash
# Create user with Standard plan
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_upgrade_canceled_user \
  --plan standard \
  --with-stripe \
  --cleanup-first

# Set to canceled state
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='test_billing_upgrade_canceled_user')
sub = Subscription.objects.get(user=user, status='active')
sub.auto_renew = False
sub.save()
print('✓ Set subscription to canceled state (auto_renew=False)')
"
```

---

### Step 2: Browser Test - Login and Upgrade

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_upgrade_canceled_user` / `Test123456!`
4. Click "Plan & Billing"
5. Verify Standard Plan with Auto Renew "No"
6. Verify both "Resume Subscription" and "Upgrade to Pro Plan" buttons visible
7. Click "Upgrade to Pro Plan" button
8. Wait for redirect to Stripe Checkout

**Stripe Checkout Verification:**
- ✅ Redirected to Stripe checkout
- ✅ Price shows $29.99/month
- ✅ Payment form visible

---

### Step 3: Complete Stripe Payment

**Stripe Test Card:**
- Card: `4242424242424242`
- Expiry: `1228`
- CVC: `123`
- Name: `Test User`

**Actions:**
1. Fill in all payment details
2. Click "Subscribe" button
3. Wait for processing (5-10 seconds)

**Expected Results:**
- ✅ Payment processed successfully
- ✅ Redirected back to http://localhost:8000/billing
- ✅ Success message: "Payment successful! Your subscription is now active."
- ✅ Plan changed to "Pro Plan" (Active)
- ✅ Credits updated to "500 / 500"
- ✅ Auto Renew shows "Yes" (new subscription)
- ✅ "Downgrade to Starter Plan" button visible
- ✅ "Cancel Subscription" button visible

**Important Note:**
Upgrading from a canceled subscription creates a **new subscription**:
- Old Standard subscription → remains canceled
- New Pro subscription → created and active
- Auto-renew → enabled on new subscription

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_upgrade_canceled_user \
  --expect-plan pro
```

**Expected Output:**
```
✓ Subscription verification passed
  Plan: pro
  Status: active
  Auto-renew: True
✓ Credits verification passed
  Base: 500
  Available: 500
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_upgrade_canceled_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: User can upgrade from a canceled (but active) subscription to a higher plan. New subscription is created.
