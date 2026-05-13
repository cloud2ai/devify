"""
EmailMessage Serializers

Serializers for EmailMessage model CRUD operations.
"""

import re

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailMessage
from .base import UserSerializer
from .email_attachment import (
    EmailAttachmentMinimalSerializer,
    EmailAttachmentNestedSerializer,
)
from .email_todo import EmailTodoListSerializer
from .share_link import ThreadlineShareLinkSerializer
from relay.models import RelayDelivery, RelayEvent


def _get_latest_share_link(instance):
    """
    Retrieve latest share link, prioritizing prefetched data.
    """
    cache = getattr(instance, "_prefetched_objects_cache", None)
    if cache and "share_links" in cache:
        prefetched = cache["share_links"]
        if prefetched:
            for link in prefetched:
                if link.is_active:
                    return link
            return None

    return (
        instance.share_links.filter(is_active=True)
        .order_by("-created_at")
        .first()
    )


def _get_latest_issue(instance):
    """
    Retrieve the direct issue for the current record only.
    """
    cache = getattr(instance, "_prefetched_objects_cache", None)
    if cache and "issues" in cache:
        prefetched = cache["issues"]
        if prefetched:
            return prefetched[0]
        return None

    return instance.issues.order_by("-created_at", "-id").first()


def _get_cached_latest_issue(instance):
    """
    Cache the latest issue on the instance to avoid repeated traversal.
    """
    cache_attr = "_cached_latest_issue"
    if hasattr(instance, cache_attr):
        return getattr(instance, cache_attr)

    issue = _get_latest_issue(instance)
    setattr(instance, cache_attr, issue)
    return issue


def _get_latest_relay_event(instance):
    """
    Retrieve the latest relay event for the current email message.
    """
    cache = getattr(instance, "_prefetched_objects_cache", None)
    if cache and "relay_events" in cache:
        prefetched = cache["relay_events"]
        if prefetched:
            return sorted(
                prefetched,
                key=lambda item: (
                    item.created_at or item.processed_at,
                    item.id,
                ),
                reverse=True,
            )[0]
        return None

    return (
        instance.relay_events.order_by("-created_at", "-id")
        .prefetch_related("deliveries", "deliveries__subscription")
        .first()
    )


def _get_cached_latest_relay_event(instance):
    """
    Cache the latest relay event on the instance to avoid repeated traversal.
    """
    cache_attr = "_cached_latest_relay_event"
    if hasattr(instance, cache_attr):
        return getattr(instance, cache_attr)

    event = _get_latest_relay_event(instance)
    setattr(instance, cache_attr, event)
    return event


def _get_relay_deliveries(instance):
    """
    Return relay deliveries from the latest relay event.
    """
    event = _get_cached_latest_relay_event(instance)
    if not event:
        return []

    cache = getattr(event, "_prefetched_objects_cache", None)
    if cache and "deliveries" in cache:
        deliveries = cache["deliveries"]
    else:
        deliveries = event.deliveries.select_related("subscription").all()

    ordered = sorted(
        deliveries,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    )
    return ordered


def _serialize_relay_delivery(delivery):
    subscription = getattr(delivery, "subscription", None)
    return {
        "id": delivery.id,
        "target_type": delivery.target_type,
        "status": delivery.status,
        "external_id": delivery.external_id,
        "external_url": delivery.external_url,
        "subscription_name": subscription.name if subscription else None,
        "subscription_enabled": (
            subscription.enabled if subscription is not None else None
        ),
        "created_at": delivery.created_at,
        "updated_at": delivery.updated_at,
    }


def _collect_issue_cluster(instance):
    """
    Collect direct issues from the merged cluster for on-demand expansion.
    """
    visited: set[int] = set()
    cluster: list[dict] = []

    def direct_issue(obj):
        cache = getattr(obj, "_prefetched_objects_cache", None)
        if cache and "issues" in cache:
            prefetched = cache["issues"]
            if prefetched:
                return prefetched[0]
            return None

        return obj.issues.order_by("-created_at", "-id").first()

    def walk(obj, depth=0):
        if not obj or obj.id in visited:
            return
        visited.add(obj.id)

        issue = direct_issue(obj)
        if issue:
            cluster.append(
                {
                    "email_id": obj.id,
                    "email_uuid": str(obj.uuid),
                    "subject": obj.subject,
                    "merged_into_id": obj.merged_into_id,
                    "merged_into_uuid": (
                        str(obj.merged_into.uuid)
                        if obj.merged_into_id and obj.merged_into
                        else None
                    ),
                    "issue_id": issue.id,
                    "issue_external_id": issue.external_id,
                    "issue_url": issue.issue_url,
                    "depth": depth,
                }
            )

        if obj.merged_into_id and obj.merged_into:
            walk(obj.merged_into, depth + 1)

        for child in obj.merged_children.all():
            walk(child, depth + 1)

    walk(instance)
    return cluster


class EmailMessageMergeChildSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for merged child records.
    """

    merged_into_uuid = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            "id",
            "uuid",
            "message_id",
            "subject",
            "summary_title",
            "received_at",
            "merge_reason",
            "merged_into",
            "merged_into_uuid",
            "status",
        ]
        read_only_fields = fields

    def get_merged_into_uuid(self, obj):
        """Get the UUID of the message this was merged into."""
        if obj.merged_into_id and obj.merged_into:
            return str(obj.merged_into.uuid)
        return None


class EmailMessageSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailMessage model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    is_canonical = serializers.SerializerMethodField()
    merged_into_uuid = serializers.SerializerMethodField()
    merged_into_subject = serializers.SerializerMethodField()
    merged_into_summary_title = serializers.SerializerMethodField()
    merged_into_message_id = serializers.SerializerMethodField()
    merged_into_received_at = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    todos = serializers.SerializerMethodField()
    merged_children = serializers.SerializerMethodField()
    share_status = serializers.SerializerMethodField()
    issue_external_id = serializers.SerializerMethodField()
    issue_url = serializers.SerializerMethodField()
    relay_delivery_count = serializers.SerializerMethodField()
    relay_deliveries = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            "id",
            "uuid",
            "user",
            "user_id",
            "message_id",
            "subject",
            "sender",
            "recipients",
            "received_at",
            "html_content",
            "text_content",
            "summary_title",
            "summary_content",
            "summary_priority",
            "summary_data",
            "todos",
            "llm_content",
            "metadata",
            "status",
            "status_display",
            "is_canonical",
            "merged_into",
            "merged_into_uuid",
            "merged_into_subject",
            "merged_into_summary_title",
            "merged_into_message_id",
            "merged_into_received_at",
            "merge_reason",
            "last_merged_at",
            "raw_message_id",
            "in_reply_to",
            "references",
            "error_message",
            "attachments",
            "merged_children",
            "share_status",
            "issue_external_id",
            "issue_url",
            "relay_delivery_count",
            "relay_deliveries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "status",
            "merged_into",
            "merge_reason",
            "last_merged_at",
            "created_at",
            "updated_at",
        ]

    def get_attachments(self, obj) -> list:
        """
        Get attachments for this email message

        Returns:
            list: List of attachment data dictionaries
        """
        attachments = obj.attachments.all()
        return EmailAttachmentNestedSerializer(
            attachments,
            many=True,
            context=self.context,
        ).data

    def get_todos(self, obj) -> list:
        """
        Get TODOs for this email message

        Returns:
            list: List of TODO data dictionaries
        """
        todos = obj.todos.all().order_by("created_at")
        return EmailTodoListSerializer(
            todos,
            many=True,
            context=self.context,
        ).data

    def get_merged_children(self, obj) -> list:
        """
        Return merged child records for canonical entries only.
        """
        children = obj.merged_children.all().order_by("received_at", "id")
        if not children:
            return []

        return EmailMessageMergeChildSerializer(
            children,
            many=True,
            context=self.context,
        ).data

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist"),
            )

        # Check if user can access this message
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create messages for yourself"),
                )

        return value

    def validate_message_id(self, value):
        """
        Validate message ID format and uniqueness
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                _("Message ID cannot be empty"),
            )

        # Check for duplicate message ID for the same user
        user_id = self.initial_data.get("user_id")
        if user_id:
            queryset = EmailMessage.objects.filter(
                user_id=user_id,
                message_id=value,
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    _("A message with this ID already exists for this user"),
                )

        return value.strip()

    def validate_status(self, value):
        """
        Validate status transition
        """
        if self.instance and self.instance.status != value:
            from ..state_machine import EMAIL_STATE_MACHINE, can_transition_to

            if not can_transition_to(
                self.instance.status,
                value,
                EMAIL_STATE_MACHINE,
            ):
                raise serializers.ValidationError(
                    _("Invalid status transition from {} to {}").format(
                        self.instance.status,
                        value,
                    ),
                )

        return value

    def _replace_image_placeholders_with_urls(
        self,
        content: str,
        attachment_url_map: dict,
    ) -> str:
        """
        Replace image placeholders with Markdown image syntax.

        Args:
            content: Content with [IMAGE: filename] placeholders
            attachment_url_map: Dict mapping safe_filename to URL

        Returns:
            str: Content with placeholders replaced by ![](url)
        """
        if not content:
            return content

        pattern = r"\[IMAGE:\s*([^\]]+)\]"

        def replacer(match):
            filename = match.group(1).strip()
            url = attachment_url_map.get(filename, "")
            return f"![]({url})" if url else match.group(0)

        return re.sub(pattern, replacer, content)

    def to_representation(self, instance):
        """
        Convert instance to representation with image placeholders replaced.

        Dynamically generates URLs from attachment file_path for automatic
        backward compatibility with both old (email_id) and new (uuid) paths.

        Args:
            instance: EmailMessage instance

        Returns:
            dict: Serialized data with replaced image placeholders
        """
        data = super().to_representation(instance)

        # Check if this is a list view by checking if parent serializer
        # has many=True
        is_list_view = self.parent is not None

        # Only limit content for list views to reduce payload size
        # Detail views should return full content
        if is_list_view:
            # Remove large content fields to reduce payload size
            data.pop("html_content", None)

            # Limit text_content and llm_content for preview
            max_length = 500
            if data.get("text_content"):
                if len(data["text_content"]) > max_length:
                    text_content = data["text_content"][:max_length] + "..."
                    data["text_content"] = text_content

            if data.get("llm_content"):
                if len(data["llm_content"]) > max_length:
                    llm_content = data["llm_content"][:max_length] + "..."
                    data["llm_content"] = llm_content

        # Build filename to URL mapping from attachments
        # Extract relative path from file_path
        # (supports both email_217/file.jpg and uuid/file.jpg)
        attachment_url_map = {}
        for att in instance.attachments.all():
            if att.is_image and att.file_path:
                rel_path = att.file_path.replace(
                    settings.EMAIL_ATTACHMENT_DIR + "/",
                    "",
                ).lstrip("/")

                # Generate URL
                if settings.ATTACHMENT_BASE_URL:
                    url = (
                        f"{settings.ATTACHMENT_BASE_URL}/attachments/"
                        f"{rel_path}"
                    )
                else:
                    url = f"/attachments/{rel_path}"

                attachment_url_map[att.safe_filename] = url

        # Replace placeholders in all content fields
        for field in ["llm_content", "summary_content"]:
            if data.get(field):
                data[field] = self._replace_image_placeholders_with_urls(
                    data[field],
                    attachment_url_map,
                )

        return data

    def get_share_status(self, obj):
        """
        Serialize share status for consumers.
        """
        share_link = _get_latest_share_link(obj)
        if not share_link:
            return None

        serializer = ThreadlineShareLinkSerializer(
            share_link,
            context={"request": self.context.get("request")},
        )
        return serializer.data

    def get_issue_external_id(self, obj):
        """
        Return latest issue external ID for the threadline.
        """
        issue = _get_cached_latest_issue(obj)
        if not issue:
            return None
        return issue.external_id

    def get_issue_url(self, obj):
        """
        Return latest issue URL for the threadline.
        """
        issue = _get_cached_latest_issue(obj)
        if not issue:
            return None
        return issue.issue_url

    def get_relay_delivery_count(self, obj):
        """
        Return the number of relay deliveries in the latest relay event.
        """
        return len(_get_relay_deliveries(obj))

    def get_relay_deliveries(self, obj):
        """
        Return the latest relay deliveries for the threadline.
        """
        return [_serialize_relay_delivery(item) for item in _get_relay_deliveries(obj)]

    def get_is_canonical(self, obj):
        """
        Return whether the row is the canonical record for display.
        """
        return obj.merged_into_id is None

    def get_merged_into_uuid(self, obj):
        """
        Return the canonical UUID for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return str(obj.merged_into.uuid)
        return None

    def get_merged_into_subject(self, obj):
        """
        Return the canonical subject for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.subject
        return None

    def get_merged_into_summary_title(self, obj):
        """
        Return the canonical summary title for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.summary_title
        return None

    def get_merged_into_message_id(self, obj):
        """
        Return the canonical message ID for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.message_id
        return None

    def get_merged_into_received_at(self, obj):
        """
        Return the canonical received time for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.received_at
        return None


class EmailMessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views - only essential fields
    """

    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    is_canonical = serializers.SerializerMethodField()
    has_merged_children = serializers.SerializerMethodField()
    merged_into_uuid = serializers.SerializerMethodField()
    merged_into_subject = serializers.SerializerMethodField()
    merged_into_summary_title = serializers.SerializerMethodField()
    merged_into_message_id = serializers.SerializerMethodField()
    merged_into_received_at = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    share_status = serializers.SerializerMethodField()
    issue_external_id = serializers.SerializerMethodField()
    issue_url = serializers.SerializerMethodField()
    relay_delivery_count = serializers.SerializerMethodField()
    relay_deliveries = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            "id",
            "uuid",
            "message_id",
            "subject",
            "sender",
            "recipients",
            "received_at",
            "summary_title",
            "summary_content",
            "summary_priority",
            "status",
            "status_display",
            "is_canonical",
            "has_merged_children",
            "merged_into",
            "merged_into_uuid",
            "merged_into_subject",
            "merged_into_summary_title",
            "merged_into_message_id",
            "merged_into_received_at",
            "merge_reason",
            "last_merged_at",
            "raw_message_id",
            "in_reply_to",
            "references",
            "attachments_count",
            "attachments",
            "metadata",
            "share_status",
            "issue_external_id",
            "issue_url",
            "relay_delivery_count",
            "relay_deliveries",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "status",
            "created_at",
        ]

    def get_attachments_count(self, obj):
        """Return count of attachments"""
        return obj.attachments.count()

    def get_attachments(self, obj):
        """Return minimal attachment info"""
        attachments = obj.attachments.all()
        return EmailAttachmentMinimalSerializer(attachments, many=True).data

    def to_representation(self, instance):
        """Limit summary_content length for list views"""
        data = super().to_representation(instance)

        # Limit summary_content for preview
        if data.get("summary_content"):
            max_length = 500
            if len(data["summary_content"]) > max_length:
                data["summary_content"] = (
                    data["summary_content"][:max_length] + "..."
                )

        return data

    def get_share_status(self, obj):
        """
        Provide lightweight share status data.
        """
        share_link = _get_latest_share_link(obj)
        if not share_link:
            return None

        serializer = ThreadlineShareLinkSerializer(
            share_link,
            context={"request": self.context.get("request")},
        )
        return serializer.data

    def get_issue_external_id(self, obj):
        """
        Return latest issue external ID for the threadline.
        """
        issue = _get_cached_latest_issue(obj)
        if not issue:
            return None
        return issue.external_id

    def get_issue_url(self, obj):
        """
        Return latest issue URL for the threadline.
        """
        issue = _get_cached_latest_issue(obj)
        if not issue:
            return None
        return issue.issue_url

    def get_relay_delivery_count(self, obj):
        """
        Return the number of relay deliveries in the latest relay event.
        """
        return len(_get_relay_deliveries(obj))

    def get_relay_deliveries(self, obj):
        """
        Return the latest relay deliveries for the threadline.
        """
        return [_serialize_relay_delivery(item) for item in _get_relay_deliveries(obj)]

    def get_is_canonical(self, obj):
        """
        Return whether the row is the canonical record for display.
        """
        return obj.merged_into_id is None

    def get_has_merged_children(self, obj):
        """
        Return whether canonical rows have merged child records.
        """
        if obj.merged_into_id is not None:
            return False

        cache = getattr(obj, "_prefetched_objects_cache", None)
        if cache and "merged_children" in cache:
            return bool(cache["merged_children"])

        return obj.merged_children.exists()

    def get_merged_into_uuid(self, obj):
        """
        Return the canonical UUID for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return str(obj.merged_into.uuid)
        return None

    def get_merged_into_subject(self, obj):
        """
        Return the canonical subject for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.subject
        return None

    def get_merged_into_summary_title(self, obj):
        """
        Return the canonical summary title for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.summary_title
        return None

    def get_merged_into_message_id(self, obj):
        """
        Return the canonical message ID for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.message_id
        return None

    def get_merged_into_received_at(self, obj):
        """
        Return the canonical received time for merged child rows.
        """
        if obj.merged_into_id and obj.merged_into:
            return obj.merged_into.received_at
        return None


class EmailMessageCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            "user_id",
            "message_id",
            "subject",
            "sender",
            "recipients",
            "received_at",
            "html_content",
            "text_content",
            "raw_message_id",
            "in_reply_to",
            "references",
        ]

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        # Auto-set user from request
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return request.user.id

        if value is None:
            raise serializers.ValidationError(
                _("User ID is required"),
            )

        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist"),
            )

    def create(self, validated_data):
        """
        Create a new email message instance
        """
        # Ensure user_id is set from request context if not provided
        request = self.context.get("request")
        if (
            request
            and hasattr(request, "user")
            and "user_id" not in validated_data
        ):
            validated_data["user_id"] = request.user.id

        return super().create(validated_data)


class EmailMessageUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            "subject",
            "sender",
            "recipients",
            "html_content",
            "text_content",
            "summary_title",
            "summary_content",
            "summary_priority",
            "summary_data",
            "llm_content",
            "status",
            "error_message",
        ]


class EmailMessageMergeSerializer(serializers.Serializer):
    """
    Request serializer for manual batch merge operations.
    """

    source_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2,
        max_length=5,
    )
    merge_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )

    def validate_source_uuids(self, value):
        """
        Deduplicate UUIDs while preserving input order.
        """
        unique_values = list(dict.fromkeys(value))
        if len(unique_values) < 2:
            raise serializers.ValidationError(
                _("At least two unique messages are required")
            )
        if len(unique_values) > 5:
            raise serializers.ValidationError(
                _("You can merge at most five messages at a time")
            )
        return unique_values


class EmailMessageBatchRetrySerializer(serializers.Serializer):
    """
    Request serializer for batch retry operations.
    """

    source_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=20,
    )
    language = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=32,
    )
    scene = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=64,
    )
    force = serializers.BooleanField(required=False, default=False)

    def validate_source_uuids(self, value):
        """
        Deduplicate UUIDs while preserving input order.
        """
        unique_values = list(dict.fromkeys(value))
        if not unique_values:
            raise serializers.ValidationError(
                _("At least one message is required")
            )
        if len(unique_values) > 20:
            raise serializers.ValidationError(
                _("You can retry at most twenty messages at a time")
            )
        return unique_values
