from django.db import migrations, transaction


def forwards(apps, schema_editor):
    PaymentProvider = apps.get_model('billing', 'PaymentProvider')
    Subscription = apps.get_model('billing', 'Subscription')
    PlanPrice = apps.get_model('billing', 'PlanPrice')
    PaymentRecord = apps.get_model('billing', 'PaymentRecord')

    with transaction.atomic():
        platform_provider = PaymentProvider.objects.filter(
            name='platform'
        ).first()
        internal_provider = PaymentProvider.objects.filter(
            name='internal'
        ).first()

        if internal_provider and platform_provider and (
            internal_provider.id != platform_provider.id
        ):
            Subscription.objects.filter(provider=internal_provider).update(
                provider=platform_provider
            )
            PlanPrice.objects.filter(provider=internal_provider).update(
                provider=platform_provider
            )
            PaymentRecord.objects.filter(provider=internal_provider).update(
                provider=platform_provider
            )
            internal_provider.delete()
            platform_provider.display_name = 'Platform'
            platform_provider.save(update_fields=['display_name'])
            return

        if internal_provider:
            internal_provider.name = 'platform'
            internal_provider.display_name = 'Platform'
            internal_provider.save(update_fields=['name', 'display_name'])
            return

        if platform_provider and platform_provider.display_name != 'Platform':
            platform_provider.display_name = 'Platform'
            platform_provider.save(update_fields=['display_name'])


def backwards(apps, schema_editor):
    PaymentProvider = apps.get_model('billing', 'PaymentProvider')
    Subscription = apps.get_model('billing', 'Subscription')
    PlanPrice = apps.get_model('billing', 'PlanPrice')
    PaymentRecord = apps.get_model('billing', 'PaymentRecord')

    with transaction.atomic():
        internal_provider = PaymentProvider.objects.filter(
            name='internal'
        ).first()
        platform_provider = PaymentProvider.objects.filter(
            name='platform'
        ).first()

        if platform_provider and internal_provider and (
            platform_provider.id != internal_provider.id
        ):
            Subscription.objects.filter(provider=platform_provider).update(
                provider=internal_provider
            )
            PlanPrice.objects.filter(provider=platform_provider).update(
                provider=internal_provider
            )
            PaymentRecord.objects.filter(provider=platform_provider).update(
                provider=internal_provider
            )
            platform_provider.delete()
            internal_provider.display_name = 'Internal'
            internal_provider.save(update_fields=['display_name'])
            return

        if platform_provider:
            platform_provider.name = 'internal'
            platform_provider.display_name = 'Internal'
            platform_provider.save(update_fields=['name', 'display_name'])
            return

        if internal_provider and internal_provider.display_name != 'Internal':
            internal_provider.display_name = 'Internal'
            internal_provider.save(update_fields=['display_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_billingauditlog'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
