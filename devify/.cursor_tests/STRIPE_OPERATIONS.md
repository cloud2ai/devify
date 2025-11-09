# Stripe Operations Guide for E2E Tests

## Overview

This guide explains how to interact with Stripe checkout pages during E2E testing using Cursor browser tools.

## Scenarios Requiring Stripe Payment

| Scenario | Stripe Action | Payment Type |
|----------|---------------|--------------|
| billing_01_subscribe | New subscription | Full price ($9.99 or $29.99) |
| billing_02_upgrade | Upgrade subscription | Prorated difference |
| billing_06_upgrade_canceled | New subscription (replace canceled) | Full price ($29.99) |

**Note:** Scenarios 3 (downgrade), 4 (cancel), and 5 (resume) do NOT require Stripe payment.

## Stripe Checkout Page Elements

When you click "Upgrade to XXX Plan", the app redirects to Stripe checkout page with these fields:

### Payment Form Fields

1. **Card Number Field** (iframe)
   - Input: `4242 4242 4242 4242` (test card)
   - Format: Automatically spaces as `4242 4242 4242 4242`

2. **Expiry Date Field**
   - Input: `1228` or `12/28`
   - Format: MM/YY

3. **CVC Field**
   - Input: `123`
   - Any 3 digits work

4. **Cardholder Name**
   - Input: Any name (e.g., `Test User`)

5. **Country Dropdown** (optional)
   - Pre-selected: China (中国)
   - Can change to United States or keep default

6. **Subscribe/Pay Button**
   - Text varies: "订阅", "Subscribe", "Pay"
   - Click to submit payment

## Cursor Browser Operations

### Step-by-Step Stripe Form Filling

```markdown
1. Wait for Stripe page to load (3-5 seconds)
2. Locate card number input field
3. Type: 4242 4242 4242 4242
4. Locate expiry field
5. Type: 1228
6. Locate CVC field
7. Type: 123
8. Locate name field
9. Type: Test User
10. Click payment button
11. Wait for processing (5-10 seconds)
12. Verify redirect to localhost:8000/billing
```

### Using Cursor Commands

When executing scenarios 1, 2, or 6, you can tell Cursor:

```
"Fill in the Stripe payment form with test card 4242 4242 4242 4242"
```

Cursor will:
- Locate the iframe containing payment fields
- Fill in card number
- Fill in expiry date
- Fill in CVC
- Fill in name
- Click the payment button

## Test Card Information

### Primary Test Card (Always Succeeds)
```
Card: 4242 4242 4242 4242
Exp: 12/28
CVC: 123
```

### Alternative Test Cards

**Visa (Successful)**
```
4242 4242 4242 4242
```

**Mastercard (Successful)**
```
5555 5555 5555 4444
```

**Declined Card**
```
4000 0000 0000 0002
```

**Insufficient Funds**
```
4000 0000 0000 9995
```

## Expected Behavior After Payment

### For New Subscription (Scenario 1)

1. Stripe processes payment
2. Redirects to: `http://localhost:8000/billing?success=true`
3. Stripe sends webhooks:
   - `customer.subscription.created`
   - `invoice.payment_succeeded`
4. Frontend shows:
   - Success message
   - New plan (Basic or Pro)
   - Updated credits (100 or 500)

### For Upgrade (Scenario 2)

1. Stripe processes prorated payment
2. Redirects back to billing page
3. Stripe sends webhook: `customer.subscription.updated`
4. Frontend shows:
   - Immediate plan change (Basic → Pro)
   - Credits updated (100 → 500)
   - Same period end date

## Troubleshooting

### Payment Form Not Appearing

**Issue**: Can't find card number field

**Solution**:
- Wait 5-10 seconds for Stripe iframe to load
- Payment fields are in an iframe
- Use Cursor's snapshot to locate iframe elements

### Payment Button Not Clickable

**Issue**: Button stays disabled

**Solution**:
- Ensure all required fields are filled
- Card number must be valid format
- Expiry must be future date

### Redirect Fails After Payment

**Issue**: Stays on Stripe page

**Solution**:
- Check Stripe test mode configuration
- Verify webhook endpoint is accessible
- Check Docker logs for webhook errors

## Webhook Simulation (Alternative)

If Stripe payment is problematic, you can simulate the result by manually triggering webhooks:

```bash
# Simulate successful subscription creation
docker exec devify-api-dev python manage.py shell -c "
from billing.services.subscription_service import SubscriptionService
# ... trigger webhook manually
"
```

**Note:** Real Stripe payment testing is preferred for E2E tests.

## Testing Without Stripe Payment

For quick testing that skips Stripe:
- Test scenarios 3, 4, 5 (no payment required)
- Use helper scripts to set subscription state directly
- Focus on UI interactions and database state

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
