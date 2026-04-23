# Generated manually for Threadline workflow runtime bindings.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("threadline", "0026_limit_password_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="ThreadlineWorkflowConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "workflow_key",
                    models.CharField(
                        default="threadline",
                        help_text="Workflow identifier for runtime bindings",
                        max_length=64,
                        unique=True,
                        verbose_name="Workflow Key",
                    ),
                ),
                (
                    "llm_config_uuid",
                    models.UUIDField(
                        blank=True,
                        help_text="Bound agentcore-metering LLM config UUID",
                        null=True,
                        verbose_name="LLM Config UUID",
                    ),
                ),
                (
                    "notification_channel_uuid",
                    models.UUIDField(
                        blank=True,
                        help_text="Bound agentcore-notifier channel UUID",
                        null=True,
                        verbose_name="Notification Channel UUID",
                    ),
                ),
                (
                    "task_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Threadline-specific runtime configuration payload",
                        verbose_name="Task Config",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this workflow binding is active",
                        verbose_name="Active",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Threadline Workflow Config",
                "verbose_name_plural": "Threadline Workflow Configs",
                "ordering": ["workflow_key"],
            },
        ),
    ]
