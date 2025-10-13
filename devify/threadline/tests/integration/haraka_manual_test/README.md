# Haraka Email Integration Manual Test

## 🚀 Quick Start

### Ready to Test!

Complete Haraka email receiving workflow test is ready. **No pytest dependency**, safe to run.

### Quick Run Commands

**Basic run:**
```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py
```

**With automatic cleanup:**
```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py \
    --cleanup
```

**Verbose mode:**
```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py \
    --verbose
```

**Save results to file:**
```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py \
    > test_results_$(date +%Y%m%d_%H%M%S).txt
```

### Expected Time

- **Single email**: 2-3 minutes (depends on LLM/OCR)
- **Complete test**: 5-10 minutes (3 emails processed in parallel)

---

## Overview

This test suite verifies the complete Haraka email receiving workflow without using pytest. It directly tests:

1. **User Creation** - Multiple users with auto_assign mode
2. **Email Sending** - Sample EML files to different users
3. **Email Fetching** - Haraka email fetch task execution
4. **Workflow Processing** - Complete email processing pipeline
5. **Result Verification** - Final SUCCESS status validation

## Features

✅ **No pytest dependency** - Pure Python, runs directly
✅ **Real-time progress** - Monitor processing status every 5 seconds
✅ **Complete workflow** - Tests end-to-end email processing
✅ **Data preservation** - Test data kept for inspection (optional cleanup)
✅ **Detailed reporting** - Comprehensive test results and statistics
✅ **Safe execution** - Won't clear database or affect existing users

## Directory Structure

```
haraka_manual_test/
├── __init__.py
├── run_full_test.py          # Main test script
├── test_utils.py             # Helper functions
└── README.md                 # This file
```

## Usage

### Basic Usage

```bash
# Run from inside container
cd /opt/devify
python threadline/tests/integration/haraka_manual_test/run_full_test.py

# Run from host
docker exec devify-api-dev python \\
    threadline/tests/integration/haraka_manual_test/run_full_test.py
```

### With Options

```bash
# With cleanup (removes test users after completion)
python threadline/tests/integration/haraka_manual_test/run_full_test.py --cleanup

# Verbose mode (shows detailed error traces)
python threadline/tests/integration/haraka_manual_test/run_full_test.py --verbose

# Custom timeout (default: 300 seconds)
python threadline/tests/integration/haraka_manual_test/run_full_test.py --timeout 600

# Combined options
python threadline/tests/integration/haraka_manual_test/run_full_test.py --cleanup --verbose
```

### Save Results to File

```bash
# Save output to file
docker exec devify-api-dev python \\
    threadline/tests/integration/haraka_manual_test/run_full_test.py \\
    > test_results_$(date +%Y%m%d_%H%M%S).txt
```

## Test Flow

### Step 1: Create Test Users

Creates 3 test users with auto_assign email configuration:

| User | Email | EML File | Description |
|------|-------|----------|-------------|
| testuser1_{timestamp} | testuser1_{timestamp}@devify.local | gmail_email.eml | Username-based email |
| testuser2_{timestamp} | testalias2_{timestamp}@devify.local | iphone_email.eml | Email alias |
| testuser3_{timestamp} | testalias3_{timestamp}@devify.local | wechat_email.eml | Email alias |

Each user is configured with:
- `email_config` (mode: auto_assign)
- `prompt_config` (language: en-US, scene: chat)
- `issue_config` (enable: false)

### Step 2: Send Test Emails

Sends sample EML files from `tests/fixtures/eml_samples/` to each user using the `send_test_email` management command.

### Step 3: Trigger Email Fetch

Calls the `haraka_email_fetch` Celery task to:
- Scan Haraka inbox directory
- Parse EML files
- Assign emails to users
- Save to database
- Trigger processing workflows

### Step 4: Monitor Processing

Monitors email processing status in real-time:
- Checks status every 5 seconds
- Displays progress for each user
- Waits up to 5 minutes (configurable)
- Tracks: fetched → processing → success/failed

### Step 5: Verify Results

Validates test results:
- ✓ Email status is SUCCESS
- ✓ Subject is parsed correctly
- ✓ Content is extracted
- ✓ Attachments are saved
- ✓ Processing time is recorded

## Expected Output

```
============================================================
Haraka Email Integration Full Test
============================================================

[Step 1/5] Create Test Users
  ✓ Created user: testuser1_20251013_140530
  ✓ Created user: testuser2_20251013_140530 (alias: testalias2_20251013_140530)
  ✓ Created user: testuser3_20251013_140530 (alias: testalias3_20251013_140530)
  ℹ Total: 3 users created successfully

[Step 2/5] Send Test Emails
  ✓ Sent gmail_email.eml → testuser1_20251013_140530@devify.local
  ✓ Sent iphone_email.eml → testalias2_20251013_140530@devify.local
  ✓ Sent wechat_email.eml → testalias3_20251013_140530@devify.local
  ℹ Total: 3 emails sent successfully

[Step 3/5] Trigger Email Fetch
  ✓ Called haraka_email_fetch task
  ✓ Fetched 3 emails
  ℹ Email fetch completed

[Step 4/5] Monitor Email Processing
  ℹ Monitoring email processing (timeout: 300s)...
  [30s] testuser1: processing | testuser2: processing | testuser3: processing
  [2m 30s] testuser1: success | testuser2: success | testuser3: success
  ℹ Processing completed: 3/3 emails

[Step 5/5] Verify Results

  User: testuser1_20251013_140530
  ✓ Status: SUCCESS
  ✓ Subject: Re: Urgent: Performance Issues...
  ✓ Attachments: 4 files
  ℹ Processing time: 2m 25s

  User: testuser2_20251013_140530
  ✓ Status: SUCCESS
  ✓ Subject: iPhone Email Test
  ✓ Attachments: 3 files
  ℹ Processing time: 2m 20s

  User: testuser3_20251013_140530
  ✓ Status: SUCCESS
  ✓ Subject: WeChat Forward
  ✓ Attachments: 2 files
  ℹ Processing time: 2m 23s

============================================================
Test Results Summary
============================================================
Total tests: 3
Success: 3 ✅
Failed: 0
Average processing time: 2m 23s

✅ All tests passed!

============================================================
```

## Test Data Management

### Data Preservation (Default)

By default, test data is preserved for inspection:
- Test users remain in database
- Emails and attachments are kept
- Useful for debugging and verification

### View Test Data

**View test users:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
users = User.objects.filter(username__startswith='testuser')
print(f'Test users: {users.count()}')
for u in users:
    print(f'  - {u.username}')
"
```

**View test emails:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from threadline.models import EmailMessage
from django.contrib.auth.models import User
users = User.objects.filter(username__startswith='testuser')
for u in users:
    emails = EmailMessage.objects.filter(user=u)
    print(f'{u.username}: {emails.count()} emails')
    for e in emails:
        print(f'  - {e.subject[:50]} ({e.status})')
"
```

### Manual Cleanup

**Delete test users:**
```bash
docker exec devify-api-dev python manage.py shell -c "
from django.contrib.auth.models import User
count = User.objects.filter(username__startswith='testuser').delete()[0]
print(f'✅ Deleted {count} test users')
"
```

### Automatic Cleanup

Use the `--cleanup` flag to automatically remove test users after completion:

```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py --cleanup
```

## Troubleshooting

### Test Hangs or Times Out

**Possible Causes**:
- Celery worker not running
- LLM/OCR services unavailable
- Network issues

**Solutions**:
```bash
# Check Celery worker
docker ps | grep worker

# Check worker logs
docker logs devify-worker-dev --tail 50

# Restart worker
docker-compose -f docker-compose.dev.yml restart worker
```

### Email Not Received

**Possible Causes**:
- Haraka not running
- Email directory permissions
- SMTP connection issues

**Solutions**:
```bash
# Check Haraka
docker ps | grep haraka
docker logs devify-haraka-dev --tail 50

# Check inbox directory
docker exec devify-api-dev ls -la /data/haraka/emails/inbox/

# Restart Haraka
docker-compose -f docker-compose.dev.yml restart haraka
```

### Workflow Processing Fails

**Possible Causes**:
- Missing environment variables
- LLM API configuration
- OCR service issues

**Solutions**:
```bash
# Check environment
docker exec devify-api-dev env | grep -E 'AZURE|OPENAI'

# Check email status
docker exec devify-api-dev python manage.py shell -c "
from threadline.models import EmailMessage
email = EmailMessage.objects.latest('created_at')
print(f'Status: {email.status}')
print(f'Error: {email.error_message}')
"
```

## Requirements

- Running Docker containers (app, haraka, redis, mysql, worker)
- Configured LLM API (Azure OpenAI)
- Configured OCR service (Azure Document Intelligence)
- Sample EML files in `tests/fixtures/eml_samples/`

## Exit Codes

- `0` - All tests passed
- `1` - Test failed or error occurred

## Notes

- Test creates unique users each time (timestamped)
- Default timeout is 5 minutes (300 seconds)
- Processing time depends on LLM/OCR latency
- Test data is safe (no impact on existing users)
- Admin account remains safe (admin/admin123)

## Important Reminders

1. **Admin Account**: Current admin account `admin/admin123` is safe. Please change password after login.
2. **Test Data**: Test data is preserved by default. Use `--cleanup` to remove.
3. **Execution Time**: Requires LLM and OCR processing, approximately 5-10 minutes.
4. **Container Status**: Ensure all containers are running (app, haraka, worker, redis, mysql).

## Related Documentation

- Haraka Configuration: `docker/haraka/README.md`
- Email Processing Design: `specs/haraka-email/design.md`
- State Machine: `threadline/state_machine.py`
- Workflow: `threadline/agents/workflow.py`

---

**Start testing now!** 🚀

```bash
docker exec devify-api-dev python \
    threadline/tests/integration/haraka_manual_test/run_full_test.py
```
