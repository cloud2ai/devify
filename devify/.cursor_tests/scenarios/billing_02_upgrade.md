# Billing Scenario 2: Upgrade Subscription (Starter → Pro)

## Overview
Test upgrading from Starter Plan to Pro Plan (immediate effect with proration).

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_upgrade_user`
- Password: `Test123456!`
- Initial Plan: Starter
- Initial Credits: 100/100
- Target Plan: Pro ($29.99/month, 2000 credits)

---

## Test Steps

### Step 1: Prepare Test User

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_upgrade_user \
  --plan starter \
  --with-stripe \
  --cleanup-first
```

**Expected Output:**
```
✓ Created user: test_billing_upgrade_user
✓ Base credits: 100
✓ Plan: starter
✓ Status: active
✓ Auto-renew: true
✓ Stripe subscription ID: sub_xxx
```

---

### Step 2: Browser Test - Login and Upgrade

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_upgrade_user` / `Test123456!`
4. Click "Plan & Billing" in navigation
5. Verify Starter Plan displayed with 100/100 credits
6. Click "Upgrade to Pro Plan" button
7. Wait for redirect to Stripe Checkout

**Stripe Checkout Verification:**
- ✅ Redirected to Stripe checkout
- ✅ Price shows $29.99/month (or prorated amount)
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
- ✅ Success message displayed

**Current Subscription Section Verification:**
- ✅ Plan Name: "Pro Plan"
- ✅ Status Badge: "Active" (green, right-aligned)
- ✅ Payment Provider: "Stripe"
- ✅ Period Start/End: Displayed correctly
- ✅ Auto Renew: "Yes"

**Credits Usage Verification:**
- ✅ Credits display: "2000 / 2000" (same line as title, right-aligned)
- ✅ Progress bar: 100%

**Credits Info Details (Default Expanded):**
- ✅ Email Limit: "2000 emails" / "2000 封"
- ✅ Attachment Limit: "30 attachments" / "30 个"
- ✅ Storage Quota: "20 GB"
- ✅ Data Retention: "Permanent" / "永久保留"

**Subscription Plans Section:**
- ✅ "Downgrade to Starter Plan" button visible
- ✅ "Downgrade to Standard Plan" button visible
- ✅ "Cancel Subscription" button visible

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_upgrade_user \
  --expect-plan pro
```

**Expected Output:**
```
✓ Subscription verification passed
  Plan: pro
  Status: active
  Auto-renew: True
✓ Credits verification passed
  Base: 2000
  Consumed: 0
  Available: 2000
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_upgrade_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Upgrade from Starter to Pro works correctly with immediate effect.
