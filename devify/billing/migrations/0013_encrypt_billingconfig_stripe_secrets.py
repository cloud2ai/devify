from django.db import migrations

from billing.fields import EncryptedTextField


def forwards(apps, schema_editor):
    BillingConfig = apps.get_model('billing', 'BillingConfig')
    for config in BillingConfig.objects.all():
        changed = False
        for field_name in (
            'stripe_live_secret_key',
            'stripe_test_secret_key',
            'stripe_webhook_secret',
        ):
            if getattr(config, field_name):
                changed = True
        if changed:
            config.save(
                update_fields=[
                    'stripe_live_secret_key',
                    'stripe_test_secret_key',
                    'stripe_webhook_secret',
                ]
            )


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_billingconfig_payment_record_backfill_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingconfig',
            name='stripe_live_secret_key',
            field=EncryptedTextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='billingconfig',
            name='stripe_test_secret_key',
            field=EncryptedTextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='billingconfig',
            name='stripe_webhook_secret',
            field=EncryptedTextField(blank=True, default=''),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
