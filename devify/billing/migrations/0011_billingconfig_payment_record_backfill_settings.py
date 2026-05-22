from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0010_billingconfig_payment_check_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='payment_record_backfill_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='payment_record_backfill_schedule',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='payment_record_backfill_lookback_days',
            field=models.IntegerField(default=30),
        ),
    ]
