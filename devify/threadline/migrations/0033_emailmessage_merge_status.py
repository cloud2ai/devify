from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("threadline", "0032_rename_ea_user_md5_idx_threadline__user_id_12453c_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailmessage",
            name="merge_error_message",
            field=models.TextField(
                blank=True,
                default="",
                help_text=_("Error details for merge coordination"),
                verbose_name=_("Merge Error Message"),
            ),
        ),
        migrations.AddField(
            model_name="emailmessage",
            name="merge_status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("merged", "Merged"),
                    ("skipped", "Skipped"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                default="idle",
                help_text=_("Status of merge coordination"),
                max_length=32,
                verbose_name=_("Merge Status"),
            ),
        ),
        migrations.AddIndex(
            model_name="emailmessage",
            index=models.Index(fields=["user", "merge_status"], name="threadline_user_merge_status_idx"),
        ),
    ]
