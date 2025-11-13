"""
Billing system configuration for SaaS subscription and credits management.

This module configures:
- Billing system on/off switches (for gradual rollout)
- Stripe payment integration (test/live modes)
- Credits allocation and consumption rules
- Cost tracking and refund policies
"""

import os

# ============================
# Billing System Master Controls
# ============================

# BILLING_ENABLED: Master switch for the entire billing system
# - When False: All users can execute workflows freely (development mode)
# - When True: Billing system is active, subscriptions are enforced
# - Use Case: Set to False during development/testing to avoid charges
# - Default: False (safe mode)
BILLING_ENABLED = os.getenv("BILLING_ENABLED", "false").lower() == "true"

# CREDITS_CHECK_ENABLED: Controls credits balance checking and consumption
# - When False: Workflows execute without checking/consuming credits
# - When True: Each workflow execution checks and consumes credits
# - Use Case: Can be enabled independently from BILLING_ENABLED for
#   gradual rollout (e.g., enable tracking first, then enforcement)
# - Default: False (safe mode)
# - Note: Only takes effect when BILLING_ENABLED=True
CREDITS_CHECK_ENABLED = (
    os.getenv("CREDITS_CHECK_ENABLED", "false").lower() == "true"
)

# ============================
# Stripe API Configuration
# ============================

# STRIPE_LIVE_SECRET_KEY: Stripe live mode secret API key
# - Use Case: Production environment with real payments
# - Security: Never commit this to version control
# - Format: sk_live_xxxxx
STRIPE_LIVE_SECRET_KEY = os.getenv("STRIPE_LIVE_SECRET_KEY", "")

# STRIPE_TEST_SECRET_KEY: Stripe test mode secret API key
# - Use Case: Development/staging with test payments
# - Security: Safe to use in non-production environments
# - Format: sk_test_xxxxx
# - Note: Test mode uses fake card numbers and doesn't charge real money
STRIPE_TEST_SECRET_KEY = os.getenv("STRIPE_TEST_SECRET_KEY", "")

# STRIPE_LIVE_MODE: Determines which Stripe API key to use
# - When False: Uses STRIPE_TEST_SECRET_KEY (safe for testing)
# - When True: Uses STRIPE_LIVE_SECRET_KEY (real payments)
# - Use Case: Set to True only in production
# - Default: False (test mode)
STRIPE_LIVE_MODE = os.getenv("STRIPE_LIVE_MODE", "false").lower() == "true"

# STRIPE_PUBLISHABLE_KEY: Stripe publishable key for frontend integration
# - Use Case: Client-side Stripe.js integration (future)
# - Format: pk_test_xxxxx (test) or pk_live_xxxxx (live)
# - Security: Safe to expose in frontend code
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# ============================
# dj-stripe Integration Configuration
# ============================

# DJSTRIPE_WEBHOOK_SECRET: Secret for validating Stripe webhook signatures
# - Use Case: Ensures webhooks are actually from Stripe
# - Security: Critical for webhook security, prevents spoofing
# - Format: whsec_xxxxx
# - How to get: Stripe Dashboard → Webhooks → Signing secret
DJSTRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# DJSTRIPE_FOREIGN_KEY_TO_FIELD: Field used for ForeignKey relationships
# - Value: "id" (use Stripe object IDs as foreign keys)
# - Use Case: Links dj-stripe models to Stripe objects
# - Note: Required by dj-stripe for proper object relationships
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# DJSTRIPE_USE_NATIVE_JSONFIELD: Use Django's native JSONField
# - Value: True (use Django's built-in JSONField)
# - Use Case: Better performance and Django compatibility
# - Note: Required for Django 3.1+
DJSTRIPE_USE_NATIVE_JSONFIELD = True

# DJSTRIPE_SUBSCRIBER_MODEL: Model that represents subscription subscribers
# - Value: 'auth.User' (Django's built-in User model)
# - Use Case: Links Stripe customers to Django users
# - Note: Each User automatically gets a corresponding Stripe Customer
DJSTRIPE_SUBSCRIBER_MODEL = 'auth.User'

# ============================
# Credits Allocation and Consumption
# ============================

# DEFAULT_FREE_CREDITS: Number of free credits for new users
# - Use Case: Free tier allocation, given to all new users
# - Value: 10 credits (allows 10 workflow executions per month)
# - Note: Resets every 30 days for Free Plan users
# - Business Logic: Enough for users to try the product
DEFAULT_FREE_CREDITS = int(os.getenv("DEFAULT_FREE_CREDITS", "10"))

# WORKFLOW_COST_CREDITS: Credits consumed per Email Workflow execution
# - Use Case: Defines how many credits each workflow costs
# - Value: 1 credit per execution
# - Note: Can be increased for more complex workflows in the future
# - Business Logic: Simple 1:1 ratio for easy user understanding
WORKFLOW_COST_CREDITS = int(os.getenv("WORKFLOW_COST_CREDITS", "1"))

# ============================
# Cost Tracking and Analytics
# ============================

# ENABLE_COST_TRACKING: Enable API usage tracking (LLM/OCR calls)
# - When True: Records all LLM/OCR calls to EmailWorkflowUsage model
# - When False: No usage data is collected
# - Use Case: Collect operational data for cost analysis
# - Note: Can be enabled even when billing is disabled
# - Data Collected: Token counts, call counts, success/failure status
# - Default: True (recommended for analytics)
ENABLE_COST_TRACKING = (
    os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true"
)

# ============================
# Automatic Refund Policy
# ============================

# AUTO_REFUND_SYSTEM_ERRORS: Automatically refund credits for system errors
# - When True: System errors (timeouts, 500s, API failures) trigger
#   automatic credit refunds
# - When False: All errors require manual refund review
# - Use Case: Improve user experience by auto-refunding for our mistakes
# - Error Classification: Uses ErrorClassifier to distinguish:
#   - System errors (timeout, 500, rate limit) → Auto refund
#   - User errors (invalid format, too large) → No refund
# - Default: True (user-friendly)
AUTO_REFUND_SYSTEM_ERRORS = (
    os.getenv("AUTO_REFUND_SYSTEM_ERRORS", "true").lower() == "true"
)
