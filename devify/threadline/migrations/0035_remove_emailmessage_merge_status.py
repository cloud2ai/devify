from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("threadline", "0034_remove_emailmessage_display_state"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="emailmessage",
            name="threadline_user_merge_status_idx",
        ),
        migrations.RemoveField(
            model_name="emailmessage",
            name="merge_status",
        ),
        migrations.RemoveField(
            model_name="emailmessage",
            name="merge_error_message",
        ),
    ]
