from django.db import migrations, models


def forwards(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    for plan in Plan.objects.all():
        if not plan.status:
            plan.status = 'active' if plan.is_active else 'draft'

        if plan.status != 'active':
            plan.allow_self_purchase = False
        elif plan.is_internal:
            plan.allow_self_purchase = False
        elif plan.slug == 'free':
            plan.allow_self_purchase = False
        else:
            plan.allow_self_purchase = True

        plan.is_active = plan.status == 'active'
        plan.save(update_fields=['status', 'allow_self_purchase', 'is_active'])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_rename_internal_payment_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='self_purchase_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='enabled_providers',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='plan',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[('draft', 'Draft'), ('active', 'Active')],
                default='',
                help_text='Plan lifecycle status: draft or active',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='plan',
            name='allow_self_purchase',
            field=models.BooleanField(
                default=False,
                help_text='Whether users can purchase this plan directly',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
