# E2E Test Environment Setup

## Prerequisites

### 1. Container Environment
- All Django/database operations run in: `devify-api-dev` container
- Django project path in container: `/opt/devify/`
- Script execution format:
  ```bash
  docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/xxx.py
  ```

### 2. Browser Access
- Application URL: http://localhost:8000
- Port mapped from container to host
- Cursor browser tools access directly
- **UI Language: English (en-US)**

### 3. Test User Naming

Fixed username per scenario:
- Billing scenarios: `test_billing_xxx_user`
  - `test_billing_free_user`
  - `test_billing_subscribe_user`
  - `test_billing_upgrade_user`
  - `test_billing_downgrade_user`
  - `test_billing_cancel_user`
  - `test_billing_resume_user`
  - `test_billing_upgrade_canceled_user`
- Future threadline scenarios: `test_threadline_xxx_user`
- Future account scenarios: `test_account_xxx_user`

All passwords: `Test123456!`

### 4. Pre-test Cleanup

Helper script automatically:
1. Checks for existing user with same name
2. Deletes user and all related data if exists
3. Creates fresh user with specified plan/state
4. Returns ready-to-test environment

## Execution Flow

### Step 1: Initialize Report
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/generate_report.py \
  --scenario billing_03_downgrade \
  --action init \
  --title "Subscription Downgrade (Pro to Basic)"
```

### Step 2: Setup Test Data
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
  --username test_billing_downgrade_user \
  --plan pro \
  --cleanup-first
```

### Step 3: Execute Test Steps
- Login with test user
- Perform UI operations
- Take screenshots at key steps
- Append results to report

### Step 4: Verify Results
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
  --username test_billing_downgrade_user \
  --expect-plan pro
```

### Step 5: Finalize Report
```bash
docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/generate_report.py \
  --scenario billing_03_downgrade \
  --action finalize \
  --result pass
```

## Stripe Test Cards

For scenarios that require payment (scenarios 1, 2, 6):

### Successful Payment
```
Card Number: 4242 4242 4242 4242
Expiry: 12/28 (any future date)
CVC: 123 (any 3 digits)
Name: Test User (any name)
```

### Payment Decline
```
Card Number: 4000 0000 0000 0002
```

### Requires 3D Secure
```
Card Number: 4000 0027 6000 3184
```

**Note:** Cursor browser tools can fill these fields automatically on the Stripe checkout page.

## Quick Test

Verify container access:
```bash
docker exec devify-api-dev python -c "
import django
django.setup()
from billing.models import Plan
print(f'{Plan.objects.count()} plans found')
"
```

Expected: `3 plans found`

## Django Environment Sharing

Since scripts run in container, direct access to:
- Django ORM models
- Django settings
- Database connections
- All installed Python packages

## Test Report Location

All test reports and screenshots saved to:
```
.cursor_tests/reports/
├── billing_03_downgrade_20251105_203045.md
└── screenshots/
    ├── billing_03_downgrade_20251105_203045_step2.png
    └── billing_03_downgrade_20251105_203045_step3.png
```

Reports are gitignored, only `.gitkeep` is tracked.
