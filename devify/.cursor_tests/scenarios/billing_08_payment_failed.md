# Billing Scenario 8: Payment Failure on Auto Renewal

## Overview
Test the handling of payment failure when auto-renewal is triggered.

## Prerequisites
See: [SETUP.md](../SETUP.md)

**Important**: This test requires a user with **real Stripe subscription** that has djstripe_subscription_id.
Test users created by helper scripts won't work for this scenario.

## Test User
- Username: Use existing user with Stripe subscription (e.g., `xiaoquqi`)
- Or: Create new user via Scenario 1 with real Stripe payment
- Initial Plan: Standard or Pro
- Auto-renew: true

---

## Test Steps

### Step 1: Setup - Ensure Active Subscription

**Verify existing subscription:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='xiaoquqi')
sub = Subscription.objects.filter(user=user, status='active').first()

if sub and sub.djstripe_subscription:
    print(f'✓ User has Stripe subscription')
    print(f'  Plan: {sub.plan.slug}')
    print(f'  Stripe ID: {sub.djstripe_subscription_id}')
    print(f'  Status: {sub.status}')
    print(f'  Auto-renew: {sub.auto_renew}')
else:
    print('✗ No valid subscription found')
"
```

**Expected Output:**
```
✓ User has Stripe subscription
  Plan: standard (or pro)
  Stripe ID: sub_xxxxx
  Status: active
  Auto-renew: True
```

---

### Step 2: Simulate Payment Failure via Stripe Dashboard

**Manual Steps in Stripe Dashboard:**

1. Go to Stripe Dashboard → Test Mode
2. Find the customer (xiaoquqi@gmail.com)
3. Navigate to their subscription
4. Click "Simulate" → "Payment fails"
5. Or: Update payment method to failing card `4000 0000 0000 0002`

**This will trigger:**
- Stripe sends `invoice.payment_failed` webhook
- Our system processes the webhook

---

### Step 3: Verify Webhook Processing

**Check Django logs:**
```bash
docker logs devify-api-dev --tail 50 | grep -i "payment.*failed"
```

**Expected Log Output:**
```
WARNING Payment failed for customer cus_XXX, subscription sub_XXX, attempt 1
INFO Updated subscription X to past_due status
INFO Scheduled payment failure notification for user X
```

---

### Step 4: Verify Database State Update

**Command:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
from billing.models import Subscription

user = User.objects.get(username='xiaoquqi')
sub = Subscription.objects.filter(user=user).order_by('-created_at').first()

print(f'Status: {sub.status}')
print(f'Expected: past_due')

assert sub.status == 'past_due', 'Status should be past_due'
print('✓ Status correctly updated to past_due')
"
```

**Expected Output:**
```
Status: past_due
Expected: past_due
✓ Status correctly updated to past_due
```

---

### Step 5: Verify Email Notification Sent

**Check Celery worker logs:**
```bash
docker logs devify-worker-dev --tail 50 | grep -i "payment.*notification"
```

**Expected:**
```
INFO Sent payment failure notification to user X (attempt 1, urgency: normal, language: zh-hans)
```

**Check email (if configured):**

**For English users (language='en-US'):**
- Subject: "Payment Failed - Automatic Retry Scheduled"
- Content in English
- Mentions retry attempt
- Includes link to billing page

**For Chinese users (language='zh-CN'):**
- Subject: "支付失败 - 已安排自动重试"
- Content in Chinese: "您的订阅支付失败（第 1 次尝试）..."
- 包含账单页面链接

**For Spanish users (language='es'):**
- Subject: "Pago Fallido - Reintento Automático Programado"
- Content in Spanish: "Su pago de suscripción falló..."
- Incluye enlace a la página de facturación

---

### Step 6: Frontend Verification (Future)

**Once frontend warning is implemented:**

1. Login as the user
2. Navigate to billing page
3. **Expected UI:**
   - Warning banner: "⚠️ Payment Failed - Please update your payment method"
   - Subscription shows "Past Due" status
   - "Update Payment Method" button visible

**Note**: Frontend display not yet implemented, this step is for future verification.

---

### Step 6.5: Verify Multi-language Support (Optional)

**Test with different user languages:**

```bash
# Test with Chinese user
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='xiaoquqi')
print(f'User language: {user.profile.language}')
"
```

**Expected behavior:**
- User with `language='zh-CN'` receives email in Chinese
- User with `language='en-US'` receives email in English
- User with `language='es'` receives email in Spanish
- Email subject and body match user's language preference

---

### Step 7: Test Stripe Retry Mechanism

**Stripe Automatic Retries:**
- Day 1: First retry (webhook triggered again, attempt_count=2)
- Day 3: Second retry (attempt_count=3, urgency → urgent)
- Day 5: Third retry (attempt_count=4, urgent email)
- Day 7: Final retry

**Each retry:**
- Triggers `invoice.payment_failed` webhook again
- Increment attempt_count
- Send notification with increasing urgency
- After 3rd attempt: Subject changes to "⚠️ Payment Failed - Action Required" (or localized)

**After Final Failure:**
- Stripe cancels subscription
- Triggers `customer.subscription.deleted` webhook
- User reverts to Free Plan

---

## Expected Behavior Summary

| Event | Subscription Status | User Notification | Frontend Display |
|-------|--------------------|--------------------|------------------|
| Payment Fails (1st) | active → past_due | Email sent (normal) | (future) Warning shown |
| Retry 2-3 | Remains past_due | Email sent | Warning persists |
| Final Retry Fails | past_due → canceled | Email sent (urgent) | Free Plan shown |

---

## Cleanup

```bash
# If test subscription was created, cancel it in Stripe Dashboard
# Or wait for automatic cancellation after final retry
```

---

## Alternative: Test with Webhook Simulation

If direct Stripe access is not available, simulate webhook:

```bash
docker exec devify-api-dev python manage.py shell -c "
from billing.webhooks import handle_payment_failed
from djstripe.models import Event

# Create mock event
# (Requires more complex setup - refer to djstripe docs)
"
```

---

## Test Complete

**Expected Result**:
- Subscription status updated to past_due
- Email notification sent to user
- System logs payment failure details
- Stripe retry mechanism works correctly

**Current Implementation Status**: ✅ Webhook handler enhanced with status update and notifications

---

## Notes

- This scenario requires real Stripe subscription with webhook integration
- Cannot be fully automated with test helper scripts
- Requires manual Stripe Dashboard interaction or webhook simulation
- Future: Add frontend warning display (not yet implemented)
