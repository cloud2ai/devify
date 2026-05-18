# Payment Check Design

## Summary
Add a provider-neutral payment check flow that can compare local subscription state against external payment providers, starting with Stripe. The same flow must support a manual admin action from the user subscription page and a scheduled task. The implementation should stay minimal, avoid provider-specific UI labels, and keep platform-assigned subscriptions out of payment checks.

## Goals
- Provide a top-level admin action on the user subscription page called "Payment Check" / "核对支付状态".
- Allow the admin to choose which provider to check.
- Reuse the same check logic for manual runs and scheduled runs.
- Keep the design extensible so future payment providers can be added without changing the task framework.
- Record both task execution metadata and per-user audit records.
- Support safe recovery when Stripe payment succeeded but webhook sync failed.

## Non-Goals
- Do not build a full payment reconciliation dashboard in this iteration.
- Do not auto-sync every page load.
- Do not include platform-assigned subscriptions in provider checks.
- Do not introduce a large plugin framework or extra abstraction layers beyond what is needed.
- Do not rename the existing billing domain or rebuild the subscription model.

## Current State
- The system already has:
  - `Subscription` as the local source of truth for current user subscription state.
  - `PaymentProvider` values for `platform` and `stripe`.
  - `djstripe`-based webhook sync for Stripe subscription events.
  - A manual "sync from Stripe" action on the user subscription drawer.
  - Task tracing and billing audit logging.
- The current manual sync is user-level and Stripe-specific.
- There is no provider-neutral top-level "Payment Check" action yet.
- There is no scheduled provider-neutral check task yet.

## Proposed Design

### 1. UI Entry Point
Add a top-level admin action on the user subscription page:
- Label:
  - Chinese: `核对支付状态`
  - English: `Payment Check`
- Location:
  - Top toolbar of the "用户订阅" page.
- Behavior:
  - Opens a small dialog.
  - The dialog lets the admin choose one or more enabled payment providers to check.
  - The dialog may also offer a check scope if needed later, but the first version should keep it minimal.

### 2. Provider-Neutral Check Service
Introduce one provider-neutral service that orchestrates the check:
- It receives a list of providers to check.
- It loads the provider-specific checker implementation for each provider.
- It collects results into a shared report structure.
- It writes task-trace metadata and billing audit entries.

This service is the only orchestration layer. Provider-specific logic stays in small checker classes.

### 3. Provider Checker Interface
Each provider implements the same minimal interface:
- `is_configured()`
- `list_remote_subscriptions(...)`
- `build_local_match_key(...)`
- `compare_local_and_remote(...)`
- `repair_local_state(...)`

For the first iteration, only Stripe needs an implementation. The interface should be generic enough for future providers to plug in without changing the scheduler or the UI.

### 4. Check Modes
Support two modes:
- `report_only`
  - Compare local and remote states.
  - Return a difference report.
  - Do not modify local data.
- `auto_fix_safe`
  - Compare local and remote states.
  - Auto-fix only the clearly safe cases.
  - Leave ambiguous cases as report-only items.

Safe cases should stay conservative:
- Remote active / local missing or free.
- Remote canceled / local still active on the same provider.

Ambiguous cases should remain manual:
- Plan mismatch with unclear intent.
- Provider state that cannot be mapped cleanly.

### 5. Scheduled Task
Add a periodic task that runs the same provider-neutral check service on a schedule.
- The task should be provider-neutral.
- The task should read the enabled providers from billing settings.
- The task should record run metadata with the existing task tracing system.
- The task should not affect platform-assigned subscriptions.

The scheduler should be configurable from global billing settings so admins can enable/disable automatic checks and choose which providers participate.

### 6. Task and Audit Recording
Every check run should record:
- Who triggered it, if manual.
- Which provider(s) were checked.
- How many local subscriptions were scanned.
- How many differences were found.
- How many items were auto-fixed.
- How many items failed.

Each repaired subscription should also write a billing audit log containing:
- actor information
- target user
- provider name
- before state
- after state
- check mode
- task/run identifier

## Data and Configuration
Add minimal global billing settings for payment checks:
- `payment_check_enabled`
- `payment_check_providers`
- `payment_check_schedule`

These settings should be provider-neutral and should not mention Stripe in their names.

The provider list should drive both:
- what the top-level manual UI can offer
- what the scheduled task runs

## Error Handling
- If a provider is not configured, the manual action should disable that provider and show a clear message.
- If a provider API call fails, the run should continue for other providers.
- If one subscription repair fails, the run should continue and report the failure.
- Platform-assigned subscriptions must be skipped, not modified.

## Testing
Add tests for:
- Manual payment check request creates a provider-neutral task record.
- Stripe provider is selectable and runs through the common check service.
- Platform-assigned subscriptions are skipped.
- Remote active / local missing is reported as a safe fix case.
- Remote canceled / local active is reported as a safe fix case.
- Provider errors do not stop the whole run.
- Scheduled task uses the same service as the manual action.

## Rollout Notes
- Keep the existing manual "sync from Stripe" user-level recovery action for now.
- Add the new top-level "Payment Check" as a separate, broader admin action.
- Start with Stripe only, but do not put Stripe in the task or setting names.
- Do not auto-fix on the first release unless the case is clearly safe.

