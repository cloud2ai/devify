# Billing Scenario 9: Payment Recovery (Past Due → Active)

## Overview
Test recovery from payment failure when user updates payment method or payment retry succeeds.

## Prerequisites
See: [SETUP.md](../SETUP.md)

**Prerequisite**: User subscription must be in `past_due` status (from Scenario 8).

## Test User
- Username: Use same user from Scenario 8 (e.g., `xiaoquqi`)
- Initial Status: past_due
- Initial Plan: Standard or Pro (before failure)

---

## Test Steps

### Step 1: Verify Past Due State

**Command:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='xiaoquqi')
sub = Subscription.objects.filter(user=user).order_by('-created_at').first()

print(f'Status: {sub.status}')
print(f'Plan: {sub.plan.slug}')
print(f'Auto-renew: {sub.auto_renew}')

assert sub.status == 'past_due', 'Should start from past_due status'
print('✓ Subscription in past_due status confirmed')
"
```

**Expected Output:**
```
Status: past_due
Plan: standard (or pro)
Auto-renew: True
✓ Subscription in past_due status confirmed
```

---

### Step 2: Update Payment Method in Stripe

**Option A: Via Stripe Dashboard**

1. Go to Stripe Dashboard → Test Mode
2. Find the customer
3. Navigate to Payment Methods
4. Add new valid test card: `4242 4242 4242 4242`
5. Set as default payment method
6. Trigger manual retry or wait for automatic retry

**Option B: Via Stripe Customer Portal**

1. Login to application
2. Navigate to billing page
3. Click "Manage Subscription" or "Update Payment Method"
4. Redirects to Stripe Customer Portal
5. Update card to: `4242 4242 4242 4242`
6. Save changes

---

### Step 3: Trigger Payment Retry

**Stripe Dashboard:**
- Find the failed invoice
- Click "Retry payment" button
- Payment should succeed with new card

**This triggers:**
- Stripe sends `invoice.payment_succeeded` webhook
- Our system processes recovery

---

### Step 4: Verify Webhook Processing

**Check Django logs:**
```bash
docker logs devify-api-dev --tail 50 | grep -i "payment.*succeeded\|past_due"
```

**Expected Log Output:**
```
INFO Payment succeeded for customer cus_XXX, subscription sub_XXX, amount: $9.99
INFO Recovered subscription X from past_due to active
INFO Scheduled payment failure notification for user X
```

---

### Step 5: Verify Database State Recovered

**Command:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='xiaoquqi')
sub = Subscription.objects.filter(user=user).order_by('-created_at').first()

print(f'Status: {sub.status}')
print(f'Plan: {sub.plan.slug}')
print(f'Auto-renew: {sub.auto_renew}')

assert sub.status == 'active', 'Status should be recovered to active'
print('✓ Subscription recovered to active status')
"
```

**Expected Output:**
```
Status: active
Plan: standard (or pro)
Auto-renew: True
✓ Subscription recovered to active status
```

---

### Step 6: Verify User Notification

**Check Celery worker logs:**
```bash
docker logs devify-worker-dev --tail 50 | grep -i "payment.*success"
```

**Expected:**
```
INFO Sent payment success notification to user X (language: zh-hans)
```

**Email notification (Multi-language):**

**For English users (language='en-US'):**
- Subject: "✅ Payment Successful"
- Content: "Your subscription payment of $9.99 was successful..."
- Thanks for continued subscription

**For Chinese users (language='zh-CN'):**
- Subject: "✅ 支付成功"
- Content: "您的订阅支付 $9.99 已成功..."
- 感谢您继续订阅

**For Spanish users (language='es'):**
- Subject: "✅ Pago Exitoso"
- Content: "Su pago de suscripción de $9.99 fue exitoso..."
- Gracias por continuar su suscripción

---

### Step 6.5: Verify Multi-language Email Content (Optional)

**For detailed verification:**

```bash
# Check user's language setting
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='xiaoquqi')
print(f'User language: {user.profile.language}')
print(f'Normalized: zh-CN → zh-hans')
"
```

**Verify email was sent in correct language:**
- Check worker logs for language parameter
- Confirm email content matches user's profile language
- Verify fallback to English if language not supported

---

### Step 7: Frontend Verification

**Login and check billing page:**

1. Navigate to: http://localhost:8000/login
2. Login as the user
3. Go to billing page
4. **Take screenshot**: Recovered state

**Expected UI:**
- Subscription shows "Active" status (not "Past Due")
- No warning banner (if implemented)
- Normal credits display
- "Cancel Subscription" button visible
- No error messages

---

## Expected Behavior Summary

| Step | Status | Auto-renew | Credits | UI Display |
|------|--------|------------|---------|------------|
| Start (past_due) | past_due | true | 100/500 | Warning (future) |
| Payment Updated | past_due | true | 100/500 | Warning persists |
| Payment Succeeds | active | true | 100/500 | Normal, warning cleared |

---

## State Transition Diagram

```
Subscription Status Flow:
active (payment fails) → past_due (retry 1-4) → active (payment succeeds)
                                              ↘ canceled (all retries fail)
```

---

## Cleanup

No cleanup needed - user subscription is now healthy and active again.

---

## Test Complete

**Expected Result**:
- Payment retry succeeds
- Subscription status recovered to active
- User notified of successful payment
- Service continues normally

**Implementation Status**: ✅ Webhook handler enhanced with recovery logic

---

## Notes

- This scenario tests the "happy recovery" path
- Requires real Stripe subscription and webhook
- Tests the opposite of Scenario 8 (failure → recovery)
- Validates that past_due status can be recovered
- Important for preventing false service interruptions
