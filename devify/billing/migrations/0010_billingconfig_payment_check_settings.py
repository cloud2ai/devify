from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_billingconfig_payment_callback_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='payment_check_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='payment_check_providers',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='payment_check_schedule',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
