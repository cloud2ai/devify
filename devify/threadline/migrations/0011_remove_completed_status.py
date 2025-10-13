# Generated migration
from django.db import migrations


def migrate_completed_to_success(apps, schema_editor):
    """
    Migrate all COMPLETED status records to SUCCESS status.

    Since SUCCESS is now the terminal state, all emails that
    were previously in COMPLETED state should be moved to SUCCESS.
    """
    EmailMessage = apps.get_model('threadline', 'EmailMessage')

    # Update all COMPLETED status to SUCCESS
    updated_count = EmailMessage.objects.filter(
        status='completed'
    ).update(
        status='success'
    )

    print(
        f"Migrated {updated_count} email(s) from "
        f"COMPLETED to SUCCESS status"
    )


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: convert SUCCESS back to COMPLETED if needed.

    Note: This is a lossy operation since we can't distinguish
    which SUCCESS records were originally COMPLETED.
    """
    EmailMessage = apps.get_model('threadline', 'EmailMessage')

    # In reverse, we convert SUCCESS back to COMPLETED
    # This is approximate since we can't know which were original
    updated_count = EmailMessage.objects.filter(
        status='success'
    ).update(
        status='completed'
    )

    print(
        f"Reversed {updated_count} email(s) from "
        f"SUCCESS to COMPLETED status"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('threadline', '0010_alter_emailmessage_status_alter_emailtask_task_type'),
    ]

    operations = [
        migrations.RunPython(
            migrate_completed_to_success,
            reverse_migration
        ),
    ]
