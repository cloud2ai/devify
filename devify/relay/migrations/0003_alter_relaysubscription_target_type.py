from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "relay",
            "0002_rename_relay_deliv_event_s_9f4e94_idx_relay_relay_event_i_0f5a98_idx_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="relaysubscription",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("feishu_bitable", "Feishu Bitable"),
                    ("github_issue", "GitHub Issue"),
                    ("jira", "Jira"),
                ],
                max_length=32,
                verbose_name="Target Type",
            ),
        ),
    ]
