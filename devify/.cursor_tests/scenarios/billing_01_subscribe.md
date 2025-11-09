# Billing Scenario 1: New Subscription (Free → Standard/Pro)

## Overview
Test the complete flow of subscribing from Free Plan to a paid plan (Standard or Pro).

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_subscribe_user`
- Password: `Test123456!`
- Initial Plan: Free
- Initial Credits: 5/5
- Target Plan: Standard ($9.90/month)

---

## Test Steps

### Step 1: Prepare Test User

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_subscribe_user \
  --plan free \
  --cleanup-first
```

**Expected Output:**
```
✓ Created user: test_billing_subscribe_user
✓ Base credits: 5
✓ Plan: free (no subscription)
```

---

### Step 2: Browser Test - Login and Subscribe

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_subscribe_user` / `Test123456!`
4. Click "Plan & Billing" in navigation
5. Verify Free Plan displayed with 5/5 credits
6. Click "Upgrade to Standard Plan" button
7. Wait for redirect to Stripe Checkout page

**Stripe Checkout Verification:**
- ✅ Redirected to stripe.com domain
- ✅ Page shows "Subscribe to aimychats.com"
- ✅ Price shows $9.99/month (or $9.90)
- ✅ Payment form visible
- ✅ Email pre-filled: test_billing_subscribe_user@test.local

---

### Step 3: Complete Stripe Payment

**Stripe Test Card Information:**
- Card Number: `4242 4242 4242 4242`
- Expiry: `12/28`
- CVC: `123`
- Cardholder Name: `Test User`
- Country: China (default)

**Actions:**
1. Fill in card number: `4242424242424242`
2. Fill in expiry: `1228`
3. Fill in CVC: `123`
4. Fill in name: `Test User`
5. Click "Subscribe" or payment button
6. Wait for Stripe processing (5-10 seconds)

**Expected Results:**
- ✅ Stripe payment processed successfully
- ✅ Redirected back to http://localhost:8000/billing
- ✅ Success message: "Payment successful! Your subscription is now active."

**Current Subscription Section Verification:**
- ✅ Plan Name: "Standard Plan"
- ✅ Status Badge: "Active" (green)
- ✅ Payment Provider: "Stripe"
- ✅ Period Start: Current date
- ✅ Period End: Current date + 30 days
- ✅ Remaining: "29 days" (or similar)
- ✅ Auto Renew: "Yes"

**Credits Usage Verification:**
- ✅ Progress bar displayed
- ✅ Credits display: "500 / 500" (right-aligned)

**Credits Info Details (Default Expanded):**
- ✅ Section Title: "About Credits" / "关于积分" (with info icon)
- ✅ Description: "Each credit allows you to process one email..." displayed
- ✅ Email Limit: "500 emails" / "500 封"
- ✅ Attachment Limit: "15 attachments" / "15 个" (数量，非MB)
- ✅ Storage Quota: "10 GB"
- ✅ Data Retention: "3 years" / "3年" (1095 days → formatted as years)

**Subscription Plans Section:**
- ✅ "Downgrade to Starter Plan" button visible
- ✅ "Cancel Subscription" button visible

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_subscribe_user \
  --expect-plan standard
```

**Expected Output:**
```
✓ User found: test_billing_subscribe_user
✓ Subscription verification passed
  Plan: standard
  Status: active
  Auto-renew: True
✓ Credits verification passed
  Base: 500
  Consumed: 0
  Available: 500
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_subscribe_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Free user can successfully subscribe to Standard Plan via Stripe Checkout.
