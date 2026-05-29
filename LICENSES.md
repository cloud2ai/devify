# Licensing Overview

This repository uses a mixed licensing model.

## 1. Core Platform

Unless otherwise noted, the core Devify platform is licensed under:

- `Apache License 2.0`

This includes the general platform capabilities around:

- data intake
- data processing
- conversation intelligence
- Threadline workflow
- Relay and notification orchestration
- account and general application infrastructure

## 2. Billing Module

The billing module is **not** licensed under Apache 2.0.

Billing-related code is licensed separately under the:

- `Devify Billing Commercial License`

The billing license is intended to support the following rule:

- internal company use is allowed
- external operation is prohibited without separate authorization

## 3. Billing Scope

The billing license applies to billing-related code, including but not limited to:

- `devify/billing`
- `devify/conf/billing`
- `devify/core/settings/billing.py`
- `ui/src/admin/api/billing.js`
- `ui/src/admin/pages/Billing`
- `ui/src/api/billing.js`
- `ui/src/components/billing`
- `ui/src/pages/Billing.vue`

If there is any conflict between the root Apache 2.0 license and the billing-specific license for files in the billing scope, the billing-specific license controls for those files.

## 4. Internal Use Rule for Billing

The intended rule for the billing module is:

- you may use it internally within your own company or organization
- you may modify it for internal use
- you may not operate it externally as a hosted service, SaaS offering, or commercial billing platform for third parties without separate written authorization

## 5. Trademarks

Licenses in this repository do not grant rights to use Devify trademarks, product names, logos, or branding except as separately permitted.

See:

- `TRADEMARKS.md`

## 6. Questions

If you need a separate commercial authorization for billing-related external operation, you should provide a dedicated commercial contact in your project materials.
