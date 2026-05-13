"""Relay admin registrations."""

from django.contrib import admin

from relay.models import RelayAppConfig, RelayDelivery, RelayEvent, RelaySubscription


@admin.register(RelayAppConfig)
class RelayAppConfigAdmin(admin.ModelAdmin):
    list_display = ["workflow_key", "llm_config_uuid", "is_active", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RelaySubscription)
class RelaySubscriptionAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "target_type", "enabled", "created_at"]
    list_filter = ["target_type", "enabled", "created_at"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(RelayEvent)
class RelayEventAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "email_message", "event_type", "status", "created_at"]
    list_filter = ["event_type", "status", "created_at"]
    readonly_fields = ["created_at", "processed_at", "artifact_snapshot"]


@admin.register(RelayDelivery)
class RelayDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "event",
        "subscription",
        "target_type",
        "status",
        "created_at",
    ]
    list_filter = ["target_type", "status", "created_at"]
    search_fields = ["external_id", "agentcore_task_id", "idempotency_key"]
    readonly_fields = ["created_at", "updated_at", "metadata"]

