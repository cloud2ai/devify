# Email Auto Merge Spec

## Overview

This document describes the current implemented behavior for threadline
auto-merge. The system no longer performs content aggregation during merge.
Instead, merge is a relationship-only step that records provenance between
emails while each email still completes its own workflow independently.

The source of truth for content remains the individual `EmailMessage`
record. Merge is used for traceability, grouping, and UI navigation.

## Current Behavior

### 1. Ingestion saves the raw email first

When a new email arrives, the save flow persists the raw record and its
attachments.

The persisted email includes:

- subject, sender, recipients, received time
- text and HTML body
- raw threading headers
- attachment records

Attachment reuse is handled early:

- attachments are deduplicated by `content_md5`
- previously processed attachments can reuse OCR / LLM outputs
- merge does not re-run attachment recognition

### 2. Merge is an asynchronous relationship step

The merge task runs separately from content processing.

It performs two jobs:

- identify whether the new email belongs to an existing conversation cluster
- record the relationship with `merged_into`, `merge_reason`, and related
  trace fields

Merge does **not**:

- rewrite the source email body
- move summary content to another record
- promote one message into another as a canonical content container
- reprocess attachments

## Merge Semantics

### Relationship only

The merge layer only records:

- `merged_into`
- `merge_reason`
- `last_merged_at`
- presentation state for merged / canonical display

The record that triggered the workflow keeps its own workflow results.
Another related email can still exist as a separate message and complete its
own processing independently.

### No content aggregation

Current implementation intentionally avoids merging content across records.
Each email keeps its own:

- `summary_title`
- `summary_content`
- `summary_data`
- `llm_content`
- `metadata`
- `issue` records
- todo extraction results

This keeps the content layer simple and prevents later merge steps from
overwriting earlier workflow output.

### Canonical and merged states

The UI uses presentation states to show the relationship:

- canonical records stay visible in the list
- merged children are hidden from the default list
- detail views still allow navigation between parent and child

The merge state is separate from workflow execution status.

## Workflow Flow

### 1. Save

`save_email()` stores the email record and attachments.

### 2. Merge task

`process_email_merge` checks whether the new email is related to an existing
cluster and records the relationship.

### 3. Workflow task

`process_email_workflow` runs the email-specific workflow for that record.
The workflow still operates on the current email independently.

### 4. Finalize

`workflow_finalize` stores the workflow output for the current email and
creates the issue record when needed.

Finalize does not perform a second canonical promotion step.

### Sequence

The implemented flow is intentionally linear:

1. Receive and persist the raw email.
2. Reuse attachment content when `content_md5` matches a prior attachment.
3. Enqueue the merge task for relationship tracking.
4. Run the email workflow for the current record only.
5. Finalize the current record's workflow output.
6. Expose merged / issue relationships in the UI without rewriting content.

## UI Behavior

### List page

The list page shows:

- merged badge for records that have merged children
- issue reference when an issue exists
- status badges using i18n labels

Merged children are not shown in the main list.

### Detail page

The detail page shows:

- issue reference when it exists
- merged parent link when the record was merged into another one
- merged children when present
- original email content only when summary / LLM content is absent

The original email copy action now copies the raw content directly.

## Task Tracking

Task tracking is handled by the agentcore task layer.

The project no longer keeps the legacy task cleanup flow for threadline task
execution records.

This keeps the runtime task model focused on:

- actual task execution state
- log and trace visibility
- Celery / agentcore lifecycle management

## Periodic Task Registry

The periodic registry remains a shared infrastructure layer in `core`.
It registers periodic definitions safely and idempotently.

Runtime editing of periodic task definitions is restricted to existing
records only. The admin API updates existing entries and does not create
new periodic tasks or crontabs.

## Important Notes

- Email workflow remains per-email and independent.
- Merge is for relationship tracking, not content aggregation.
- UI links between parent and child records are expected and supported.
- Issue display is based on persisted issue records, not on the current
  external sync toggle.

## Implementation Summary

- `EmailMessage` stores the raw email and workflow output.
- `merge` stores relation metadata only.
- `workflow_finalize` stores the current email's output and issue data.
- UI renders merged / issue / parent-child navigation based on persisted
  fields.

## Validation Notes

The current behavior is validated through:

- backend unit and e2e tests around merge and API serialization
- UI updates in dashboard and detail pages
- i18n translations for merged / issue / canonical labels
