"""Relay models for application-center delivery subscriptions."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class RelayAppConfig(models.Model):
    workflow_key = models.CharField(
        max_length=64,
        unique=True,
        default="relay",
        verbose_name=_("Workflow Key"),
    )
    llm_config_uuid = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Relay LLM Config UUID"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Relay App Config")
        verbose_name_plural = _("Relay App Configs")

    def __str__(self) -> str:
        return self.workflow_key


class RelaySubscription(models.Model):
    class TargetType(models.TextChoices):
        FEISHU_BITABLE = "feishu_bitable", _("Feishu Bitable")
        JIRA = "jira", _("Jira")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="relay_subscriptions",
        verbose_name=_("User"),
    )
    target_type = models.CharField(
        max_length=32,
        choices=TargetType.choices,
        verbose_name=_("Target Type"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    enabled = models.BooleanField(default=True, verbose_name=_("Enabled"))
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Config"))
    strategies = models.JSONField(
        default=dict, blank=True, verbose_name=_("Strategies")
    )
    field_mappings = models.JSONField(
        default=dict, blank=True, verbose_name=_("Field Mappings")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Relay Subscription")
        verbose_name_plural = _("Relay Subscriptions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name", "target_type"],
                name="relay_subscription_user_name_target_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["user", "enabled"]),
            models.Index(fields=["user", "target_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.target_type})"


class RelayEvent(models.Model):
    class EventType(models.TextChoices):
        WORKFLOW_COMPLETED = "workflow_completed", _("Workflow Completed")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="relay_events",
        verbose_name=_("User"),
    )
    email_message = models.ForeignKey(
        "threadline.EmailMessage",
        on_delete=models.CASCADE,
        related_name="relay_events",
        verbose_name=_("Email Message"),
    )
    event_type = models.CharField(
        max_length=64,
        choices=EventType.choices,
        default=EventType.WORKFLOW_COMPLETED,
        verbose_name=_("Event Type"),
    )
    artifact_snapshot = models.JSONField(
        default=dict, blank=True, verbose_name=_("Artifact Snapshot")
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Relay Event")
        verbose_name_plural = _("Relay Events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["event_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} #{self.id}"


class RelayDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        SKIPPED = "skipped", _("Skipped")

    event = models.ForeignKey(
        RelayEvent,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("Event"),
    )
    subscription = models.ForeignKey(
        RelaySubscription,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("Subscription"),
    )
    target_type = models.CharField(max_length=32, verbose_name=_("Target Type"))
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("External ID"),
    )
    external_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("External URL"),
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    agentcore_task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Agentcore Task ID"),
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name=_("Idempotency Key"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Relay Delivery")
        verbose_name_plural = _("Relay Deliveries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["subscription", "status"]),
            models.Index(fields=["target_type", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "subscription"],
                name="relay_delivery_event_subscription_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"{self.target_type} #{self.id}"

