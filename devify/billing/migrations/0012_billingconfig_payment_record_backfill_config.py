from django.db import migrations, models


DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE = '0 3 * * *'
DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS = 30


def forwards(apps, schema_editor):
    BillingConfig = apps.get_model('billing', 'BillingConfig')
    for config in BillingConfig.objects.all():
        config.payment_record_backfill = {
            'enabled': bool(
                getattr(config, 'payment_record_backfill_enabled', False)
            ),
            'schedule': (
                str(
                    getattr(config, 'payment_record_backfill_schedule', '')
                    or ''
                ).strip()
                or DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
            ),
            'lookback_days': max(
                int(
                    getattr(
                        config,
                        'payment_record_backfill_lookback_days',
                        DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
                    )
                    or DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS
                ),
                1,
            ),
        }
        config.save(update_fields=['payment_record_backfill'])


def backwards(apps, schema_editor):
    BillingConfig = apps.get_model('billing', 'BillingConfig')
    for config in BillingConfig.objects.all():
        backfill_config = dict(getattr(config, 'payment_record_backfill', {}) or {})
        config.payment_record_backfill_enabled = bool(
            backfill_config.get('enabled', False)
        )
        config.payment_record_backfill_schedule = (
            str(backfill_config.get('schedule') or '').strip()
            or DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
        )
        config.payment_record_backfill_lookback_days = max(
            int(backfill_config.get('lookback_days') or 0),
            1,
        )
        config.save(
            update_fields=[
                'payment_record_backfill_enabled',
                'payment_record_backfill_schedule',
                'payment_record_backfill_lookback_days',
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0011_billingconfig_payment_record_backfill_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='payment_record_backfill',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='billingconfig',
            name='payment_record_backfill_enabled',
        ),
        migrations.RemoveField(
            model_name='billingconfig',
            name='payment_record_backfill_schedule',
        ),
        migrations.RemoveField(
            model_name='billingconfig',
            name='payment_record_backfill_lookback_days',
        ),
    ]
