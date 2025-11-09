# Billing Scenario 5: Resume Subscription

## Overview
Test resuming a canceled subscription (re-enable auto-renewal).

## Prerequisites
See: [SETUP.md](../SETUP.md)

## Test User
- Username: `test_billing_resume_user`
- Password: `Test123456!`
- Initial Plan: Standard (canceled but still active)
- Initial Credits: 20/20
- Auto-renew: False (canceled)

---

## Test Steps

### Step 1: Prepare Test User with Canceled State

**Commands:**
```bash
# Create user with Standard plan
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_resume_user \
  --plan standard \
  --with-stripe \
  --cleanup-first

# Set to canceled state (auto_renew=False)
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='test_billing_resume_user')
subscription = Subscription.objects.get(user=user, status='active')
subscription.auto_renew = False
subscription.save()
print('✓ Set auto_renew to False (canceled state)')
"
```

---

### Step 2: Browser Test - Login and Resume

**Actions:**
1. Navigate to: http://localhost:8000/login
2. Switch to English (🇺🇸)
3. Login: `test_billing_resume_user` / `Test123456!`
4. Click "Plan & Billing"
5. Verify Standard Plan with Auto Renew "No"
6. Verify "Resume Subscription" button visible (green)
7. Click "Resume Subscription" button
8. Verify resume dialog appears

**Resume Dialog Verification:**
- ✅ Dialog title: "Resume Subscription"
- ✅ Message about auto-renewal
- ✅ Shows next billing date
- ✅ "Confirm Resume" button present

---

### Step 3: Confirm Resume

**Actions:**
1. Click "Confirm Resume" button
2. Wait for response

**Expected Results:**
- ✅ Dialog closed
- ✅ Success message: "Subscription resumed. Auto-renewal is now active."
- ✅ Auto Renew changed to "Yes"
- ✅ Button changed to "Cancel Subscription" (red)
- ✅ Plan remains "Standard Plan" (Active)
- ✅ Credits remain "20 / 20"

**Current Subscription UI Verification:**
- ✅ Plan Name: "Standard Plan"
- ✅ Status: "Active" (right-aligned)
- ✅ Auto Renew: "Yes" (changed from "No")
- ✅ Credits display: "20 / 20" (same line as title)
- ✅ Credits Info: Email Limit "20", Attachment "15", Storage "10 GB", Retention "3年"
- ✅ No payment required (current period already paid)

---

### Step 4: Verify Database State

**Command:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='test_billing_resume_user')
sub = Subscription.objects.get(user=user, status='active')
print(f'Plan: {sub.plan.slug}')
print(f'Auto-renew: {sub.auto_renew}')
assert sub.auto_renew == True, 'Auto-renew should be True'
print('✓ Resume verified')
"
```

**Expected Output:**
```
Plan: standard
Auto-renew: True
✓ Resume verified
```

---

## Cleanup

```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_resume_user \
  --cleanup-only
```

---

## Test Complete ✅

**Expected Result**: Canceled subscription can be resumed without payment.
