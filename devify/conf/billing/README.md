# Billing Plans Configuration

This directory contains billing plan configurations for the Devify billing system.

## Configuration File

**`plans.yaml`** - Defines all subscription plans and their pricing

### File Structure

```yaml
plans:
  - name: Plan Display Name
    slug: unique-plan-identifier
    description: Plan description shown to users
    monthly_price_cents: 499
    metadata:
      credits_per_period: 100
      period_days: 30
      workflow_cost_credits: 1
      max_email_length: 50000
      max_attachment_size_mb: 10
      storage_quota_mb: 5120
      retention_days: 365
```

### Field Descriptions

#### Plan Fields
- **name**: Display name shown to users (e.g., "Starter Plan")
- **slug**: Unique identifier (lowercase, hyphenated) used internally
- **description**: Brief description of the plan
- **monthly_price_cents**: Price in cents (e.g., 499 = $4.99)

#### Metadata Fields
- **credits_per_period**: Number of credits allocated per billing period
- **period_days**: Billing period length in days (usually 30)
- **workflow_cost_credits**: Credits consumed per workflow execution
- **max_email_length**: Maximum email content length in characters
- **max_attachment_size_mb**: Maximum attachment size in megabytes
- **storage_quota_mb**: Total storage quota in megabytes
- **retention_days**: Data retention period (-1 = unlimited)

## Usage

### Default Usage

The initialization command automatically loads `conf/billing/plans.yaml`:

```bash
python manage.py init_billing_stripe
```

### Custom Configuration File

Specify a different configuration file:

```bash
python manage.py init_billing_stripe --plans-config=/path/to/custom-plans.yaml
```

### Environment-Specific Configurations

You can maintain different plan configurations for different environments:

```bash
# Development
python manage.py init_billing_stripe --plans-config=conf/billing/plans.dev.yaml

# Production
python manage.py init_billing_stripe --plans-config=conf/billing/plans.prod.yaml
```

## Modifying Plans

### Changing Prices

1. Edit `plans.yaml` and update the `monthly_price_cents` value
2. Run `python manage.py init_billing_stripe`
3. The system will:
   - Keep the existing Stripe Product
   - Deactivate the old Price
   - Create a new Price with the updated amount

### Adding New Plans

1. Add a new plan to the `plans` list in `plans.yaml`
2. Run `python manage.py init_billing_stripe`
3. The system will create the new plan in both local database and Stripe

### Updating Metadata

1. Edit the `metadata` fields in `plans.yaml`
2. Run `python manage.py init_billing_stripe`
3. Local plan records will be updated (Stripe products remain unchanged)

## Important Notes

- **Slug must be unique**: The `slug` field is used as the unique identifier
- **Free plan required**: At least one plan with `monthly_price_cents: 0` should exist
- **Stripe sync**: Changes are automatically synced to Stripe when you run `init_billing_stripe`
- **Idempotent**: Safe to run multiple times, won't create duplicates
- **Version control**: Keep this file in version control to track pricing changes

## Example Configurations

### Minimal Free Plan Only

```yaml
plans:
  - name: Free Plan
    slug: free
    description: Free tier
    monthly_price_cents: 0
    metadata:
      credits_per_period: 10
      period_days: 30
      workflow_cost_credits: 1
```

### With Annual Pricing (Future)

```yaml
plans:
  - name: Pro Plan
    slug: pro
    description: Professional plan
    monthly_price_cents: 2999
    annual_price_cents: 29990
    metadata:
      credits_per_period: 2000
      period_days: 30
```

## Troubleshooting

### Configuration Not Loading

Check file path and permissions:
```bash
ls -la devify/conf/billing/plans.yaml
```

### YAML Syntax Errors

Validate YAML syntax:
```bash
python -c "import yaml; yaml.safe_load(open('devify/conf/billing/plans.yaml'))"
```

### Plan Not Syncing to Stripe

Check Stripe API configuration:
```bash
python manage.py init_billing_stripe --skip-products --skip-webhook
```
