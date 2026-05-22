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

# BILLING_ENABLED: Deprecated compatibility flag.
# Billing is always enabled now; startup no longer reads this flag.
BILLING_ENABLED = False

# CREDITS_CHECK_ENABLED: Legacy compatibility flag.
# Credits are always enforced at runtime.
CREDITS_CHECK_ENABLED = True

# ============================
# Stripe API Configuration
# ============================
#
# Stripe configuration is managed at runtime through BillingConfig in the
# database. These constants are intentionally left empty so environment
# variables no longer seed or override billing behavior at startup.
STRIPE_LIVE_SECRET_KEY = ""
STRIPE_TEST_SECRET_KEY = ""
STRIPE_LIVE_MODE = False
STRIPE_PUBLISHABLE_KEY = ""

# ============================
# dj-stripe Integration Configuration
# ============================

# DJSTRIPE_WEBHOOK_SECRET is managed at runtime through BillingConfig.
DJSTRIPE_WEBHOOK_SECRET = ""

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
