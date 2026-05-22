from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0008_billing_payment_governance'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='payment_callback_url',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
