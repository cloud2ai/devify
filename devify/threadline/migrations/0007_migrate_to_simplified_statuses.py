# Generated manually for status migration

from django.db import migrations


def migrate_old_statuses_to_new(apps, schema_editor):
    """
    Migrate old detailed statuses to new simplified statuses.

    Mapping:
    - All *_PROCESSING states -> PROCESSING
    - All *_SUCCESS states -> SUCCESS
    - All *_FAILED states -> FAILED
    - FETCHED stays as FETCHED
    - COMPLETED stays as COMPLETED
    """
    EmailMessage = apps.get_model('threadline', 'EmailMessage')

    # Status mapping from old to new
    status_mapping = {
        # Processing states
        'ocr_processing': 'processing',
        'llm_ocr_processing': 'processing',
        'llm_email_processing': 'processing',
        'llm_summary_processing': 'processing',
        'issue_processing': 'processing',

        # Success states
        'ocr_success': 'success',
        'llm_ocr_success': 'success',
        'llm_email_success': 'success',
        'llm_summary_success': 'success',
        'issue_success': 'success',

        # Failed states
        'ocr_failed': 'failed',
        'llm_ocr_failed': 'failed',
        'llm_email_failed': 'failed',
        'llm_summary_failed': 'failed',
        'issue_failed': 'failed',

        # Keep as is
        'fetched': 'fetched',
        'completed': 'completed',
    }

    # Count migrations for logging
    migration_counts = {}

    for old_status, new_status in status_mapping.items():
        count = EmailMessage.objects.filter(status=old_status).update(
            status=new_status
        )
        if count > 0:
            migration_counts[old_status] = count
            print(f"Migrated {count} emails from {old_status} to {new_status}")

    total_migrated = sum(migration_counts.values())
    print(f"\nTotal emails migrated: {total_migrated}")
    print(f"Migration summary: {migration_counts}")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration is not possible as we lose information
    about which specific old state each email was in.
    """
    print("Warning: Reverse migration not supported - old state information lost")
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('threadline', '0006_add_cleanup_task_types'),
    ]

    operations = [
        migrations.RunPython(
            migrate_old_statuses_to_new,
            reverse_migration
        ),
    ]
