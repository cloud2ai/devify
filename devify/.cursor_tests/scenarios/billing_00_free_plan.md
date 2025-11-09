# Billing Scenario 0: Free Plan Initial State

## Overview
Verify new user's default Free Plan state and functionality.

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_free_user`
- Password: `Test123456!`
- Initial Plan: Free
- Initial Credits: 10/10

---

## Test Steps

### Step 1: Prepare Test User

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_free_user \
  --plan free \
  --cleanup-first
```

**Expected Output:**
```
✓ Created user: test_billing_free_user
✓ Base credits: 5
✓ Plan: free (no subscription)
```

---

### Step 2: Browser Test - Login and Navigate

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch UI to English (🇺🇸 button)
3. Enter username: `test_billing_free_user`
4. Enter password: `Test123456!`
5. Click "Sign in" button
6. Click "Plan & Billing" in navigation

**Expected Results:**

**Current Subscription Section:**
- ✅ Plan Name: "Free Plan"
- ✅ Status Badge: "Active" (green, right-aligned)
- ✅ No payment provider displayed
- ✅ Period Start: "-"
- ✅ Period End: "-"
- ✅ Auto Renew: "-"

**Credits Usage:**
- ✅ Credits display: "5 / 5" (same line as title, right-aligned)
- ✅ Progress bar: 100%

**Credits Info Details (Default Expanded):**
- ✅ Email Limit: "5 emails" / "5 封"
- ✅ Attachment Limit: "5 attachments" / "5 个"
- ✅ Storage Quota: "1 GB"
- ✅ Data Retention: "30 days" / "30天"

**Subscription Plans Section:**
- ✅ "Upgrade to Starter Plan" button visible
- ✅ "Upgrade to Standard Plan" button visible
- ✅ "Upgrade to Pro Plan" button visible
- ✅ No "Downgrade" buttons
- ✅ No "Cancel Subscription" button

---

### Step 3: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_free_user \
  --expect-plan free
```

**Expected Output:**
```
✓ User found: test_billing_free_user
✓ No active subscription (Free Plan)
✓ Credits verification passed
  Base: 10
  Consumed: 0
  Available: 10
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_free_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Free Plan state correctly initialized for new users.
