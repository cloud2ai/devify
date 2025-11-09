# Billing Scenario 4: Cancel Subscription

## Overview
Test canceling an active subscription (remains active until period end).

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_cancel_user`
- Password: `Test123456!`
- Initial Plan: Standard
- Initial Credits: 20/20

---

## Test Steps

### Step 1: Prepare Test User

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_cancel_user \
  --plan standard \
  --with-stripe \
  --cleanup-first
```

**Expected Output:**
```
✓ Created user: test_billing_cancel_user
✓ Plan: standard
✓ Auto-renew: true
```

---

### Step 2: Browser Test - Login and Cancel

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_cancel_user` / `Test123456!`
4. Click "Plan & Billing"
5. Verify Standard Plan with Auto Renew "Yes"
6. Click "Cancel Subscription" button
7. Verify cancel dialog appears

**Cancel Dialog Verification:**
- ✅ Dialog title: "Cancel Subscription"
- ✅ Message about period end
- ✅ Shows: "You can continue using until [DATE]"
- ✅ "Confirm Cancellation" button present

---

### Step 3: Confirm Cancellation

**Actions:**
1. Click "Confirm Cancellation" button
2. Wait for response

**Expected Results:**
- ✅ Dialog closed
- ✅ Success message: "Subscription canceled. Will take effect at the end of current period."
- ✅ Plan still shows "Standard Plan" (Active)
- ✅ Auto Renew changed to "No"
- ✅ Button changed to "Resume Subscription" (green)
- ✅ Credits remain "20 / 20"

**Current Subscription UI Verification:**
- ✅ Plan Name: "Standard Plan"
- ✅ Status: "Active" (right-aligned)
- ✅ Auto Renew: "No" (changed from "Yes")
- ✅ Credits display: "20 / 20" (same line as title)
- ✅ Credits Info: Email Limit "20", Attachment "15", Storage "10 GB", Retention "3年"

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_cancel_user \
  --expect-plan standard
```

**Note:** Check that auto_renew is False.

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_cancel_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Cancellation works correctly, subscription remains active until period end.
