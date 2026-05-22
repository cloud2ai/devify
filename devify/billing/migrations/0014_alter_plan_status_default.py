from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0013_encrypt_billingconfig_stripe_secrets'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[('draft', 'Draft'), ('active', 'Active')],
                default='draft',
                help_text='Plan lifecycle status: draft or active',
                max_length=16,
            ),
        ),
    ]
