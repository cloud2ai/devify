"""
Billing module for SaaS subscription and credits management.

This module provides:
- Credits-based billing system
- Multi-payment provider support (Stripe, Alipay, WeChat)
- Subscription management
- Integration with dj-stripe
"""

default_app_config = 'billing.apps.BillingConfig'


