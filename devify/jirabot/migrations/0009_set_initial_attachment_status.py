# Generated manually to set initial attachment status

from django.db import migrations


def set_initial_attachment_status(apps, schema_editor):
    """
    Set initial processing status for existing attachments based on their content.
    """
    EmailAttachment = apps.get_model('jirabot', 'EmailAttachment')

    for attachment in EmailAttachment.objects.all():
        if attachment.is_image:
            # For image attachments, check OCR and LLM content
            if attachment.ocr_content and attachment.ocr_content.strip():
                if attachment.llm_content and attachment.llm_content.strip():
                    attachment.status = 'llm_success'
                else:
                    attachment.status = 'ocr_success'
            else:
                attachment.status = 'pending'
        else:
            # For non-image attachments, mark as llm_success (no processing needed)
            attachment.status = 'llm_success'

        attachment.save(update_fields=['status'])


def reverse_set_initial_attachment_status(apps, schema_editor):
    """
    Reverse migration - reset all attachment status to pending.
    """
    EmailAttachment = apps.get_model('jirabot', 'EmailAttachment')
    EmailAttachment.objects.all().update(status='pending')


class Migration(migrations.Migration):

    dependencies = [
        ('jirabot', '0008_add_attachment_status_machine'),
    ]

    operations = [
        migrations.RunPython(
            set_initial_attachment_status,
            reverse_set_initial_attachment_status
        ),
    ]
