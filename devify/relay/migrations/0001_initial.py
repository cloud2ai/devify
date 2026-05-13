from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("threadline", "0035_remove_emailmessage_merge_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="RelayAppConfig",
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
                        default="relay",
                        max_length=64,
                        unique=True,
                        verbose_name="Workflow Key",
                    ),
                ),
                (
                    "llm_config_uuid",
                    models.UUIDField(
                        blank=True,
                        null=True,
                        verbose_name="Relay LLM Config UUID",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        verbose_name="Active",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Relay App Config",
                "verbose_name_plural": "Relay App Configs",
            },
        ),
        migrations.CreateModel(
            name="RelaySubscription",
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
                    "target_type",
                    models.CharField(
                        choices=[
                            ("feishu_bitable", "Feishu Bitable"),
                            ("jira", "Jira"),
                        ],
                        max_length=32,
                        verbose_name="Target Type",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                (
                    "enabled",
                    models.BooleanField(default=True, verbose_name="Enabled"),
                ),
                (
                    "config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Config",
                    ),
                ),
                (
                    "strategies",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Strategies",
                    ),
                ),
                (
                    "field_mappings",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Field Mappings",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relay_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Relay Subscription",
                "verbose_name_plural": "Relay Subscriptions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RelayEvent",
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
                    "event_type",
                    models.CharField(
                        choices=[("workflow_completed", "Workflow Completed")],
                        default="workflow_completed",
                        max_length=64,
                        verbose_name="Event Type",
                    ),
                ),
                (
                    "artifact_snapshot",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Artifact Snapshot",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                        verbose_name="Status",
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "email_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relay_events",
                        to="threadline.emailmessage",
                        verbose_name="Email Message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relay_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Relay Event",
                "verbose_name_plural": "Relay Events",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RelayDelivery",
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
                    "target_type",
                    models.CharField(
                        max_length=32,
                        verbose_name="Target Type",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                        verbose_name="Status",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="External ID",
                    ),
                ),
                (
                    "external_url",
                    models.URLField(
                        blank=True,
                        max_length=500,
                        null=True,
                        verbose_name="External URL",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="Error"),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Metadata",
                    ),
                ),
                (
                    "agentcore_task_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=255,
                        null=True,
                        verbose_name="Agentcore Task ID",
                    ),
                ),
                (
                    "idempotency_key",
                    models.CharField(
                        db_index=True,
                        max_length=255,
                        unique=True,
                        verbose_name="Idempotency Key",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="relay.relayevent",
                        verbose_name="Event",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="relay.relaysubscription",
                        verbose_name="Subscription",
                    ),
                ),
            ],
            options={
                "verbose_name": "Relay Delivery",
                "verbose_name_plural": "Relay Deliveries",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="relaysubscription",
            constraint=models.UniqueConstraint(
                fields=("user", "name", "target_type"),
                name="relay_subscription_user_name_target_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="relaydelivery",
            constraint=models.UniqueConstraint(
                fields=("event", "subscription"),
                name="relay_delivery_event_subscription_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="relaysubscription",
            index=models.Index(fields=["user", "enabled"], name="relay_subs_user_en_6f1bb4_idx"),
        ),
        migrations.AddIndex(
            model_name="relaysubscription",
            index=models.Index(fields=["user", "target_type"], name="relay_subs_user_ta_5cd601_idx"),
        ),
        migrations.AddIndex(
            model_name="relayevent",
            index=models.Index(fields=["user", "status"], name="relay_event_user_st_7b4a71_idx"),
        ),
        migrations.AddIndex(
            model_name="relayevent",
            index=models.Index(fields=["event_type", "status"], name="relay_event_type_st_4a7a38_idx"),
        ),
        migrations.AddIndex(
            model_name="relaydelivery",
            index=models.Index(fields=["event", "status"], name="relay_deliv_event_s_9f4e94_idx"),
        ),
        migrations.AddIndex(
            model_name="relaydelivery",
            index=models.Index(fields=["subscription", "status"], name="relay_deliv_subsc_7d9a7e_idx"),
        ),
        migrations.AddIndex(
            model_name="relaydelivery",
            index=models.Index(fields=["target_type", "status"], name="relay_deliv_targe_0cae13_idx"),
        ),
    ]

