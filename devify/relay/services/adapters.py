"""Relay delivery adapters."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Dict

from relay.services.drivers.feishu_bitable_handler import (
    FeishuBitableIssueHandler,
)
from relay.services.drivers.jira_handler import JiraIssueHandler

from threadline.utils.issues.error_utils import is_missing_issue_error
from relay.services.delivery_strategy import (
    NEW_AND_LINK,
    UPDATE,
    resolve_delivery_plan,
)


@dataclass
class RelayAdapterResult:
    external_id: str | None = None
    external_url: str | None = None
    metadata: Dict[str, Any] | None = None


class BaseRelayAdapter:
    def deliver(self, *, event, subscription, delivery) -> RelayAdapterResult:
        raise NotImplementedError


def _attachment_fingerprints(attachment: Dict[str, Any]) -> list[str]:
    fingerprints: list[str] = []
    content_md5 = str(attachment.get("content_md5") or "").strip()
    if content_md5:
        fingerprints.append(f"md5:{content_md5}")

    attachment_id = attachment.get("id")
    if attachment_id not in (None, ""):
        fingerprints.append(f"id:{attachment_id}")

    filename = str(attachment.get("filename") or "unknown").strip()
    file_size = attachment.get("file_size", "")
    fingerprints.append(f"name:{filename}:{file_size}")
    return list(dict.fromkeys(fingerprints))


def _normalize_uploaded_keys(metadata: Dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []

    uploaded_keys = metadata.get("uploaded_attachment_keys", [])
    if not uploaded_keys:
        return []

    if isinstance(uploaded_keys, str):
        uploaded_keys = [uploaded_keys]

    return list(
        dict.fromkeys(
            str(uploaded_key)
            for uploaded_key in uploaded_keys
            if uploaded_key
        )
    )


def _apply_feishu_title_prefix(subscription, title: str | None) -> str:
    config = subscription.config or {}
    feishu_config = config.get("feishu_bitable") or {}
    prefix = str(feishu_config.get("summary_prefix") or "")
    base_title = str(title or "").strip()
    if not prefix:
        return base_title
    if not base_title:
        return prefix
    if base_title.startswith(prefix):
        return base_title
    return f"{prefix}{base_title}"


def _sync_jira_attachments(
    *,
    handler: JiraIssueHandler,
    issue_key: str,
    attachments: list[Dict[str, Any]],
    existing_uploaded_keys: set[str] | None = None,
    lookup_remote_uploaded_keys: bool = True,
) -> tuple[Dict[str, Any], list[str]]:
    attachments = attachments or []
    existing_keys_ordered = list(existing_uploaded_keys or [])
    existing_keys: set[str] = set(existing_keys_ordered)
    known_keys = set(existing_keys)

    if lookup_remote_uploaded_keys:
        remote_getter = getattr(handler, "get_issue_attachment_fingerprints", None)
        if callable(remote_getter):
            try:
                remote_fingerprints = remote_getter(issue_key)
                if remote_fingerprints:
                    known_keys.update(remote_fingerprints)
            except Exception:
                pass

    to_upload: list[Dict[str, Any]] = []
    skipped_keys: list[str] = []
    skipped_attachment_count = 0
    for attachment in attachments:
        fingerprints = _attachment_fingerprints(attachment)
        if any(fp in known_keys for fp in fingerprints):
            skipped_keys.extend(fingerprints)
            skipped_attachment_count += 1
        else:
            to_upload.append(attachment)

    if to_upload:
        upload_result = handler.upload_attachments(issue_key=issue_key, attachments=to_upload)
    else:
        upload_result = {
            "uploaded_count": 0,
            "skipped_count": len(attachments),
            "uploaded_attachment_keys": [],
            "skipped_attachment_keys": skipped_keys,
            "reason": "all_attachments_already_uploaded",
        }

    new_keys = upload_result.get("uploaded_attachment_keys", [])
    all_uploaded_keys = list(
        dict.fromkeys(existing_keys_ordered + list(new_keys))
    )
    upload_result["uploaded_attachment_keys"] = all_uploaded_keys
    upload_result["skipped_attachment_keys"] = list(
        dict.fromkeys(skipped_keys + upload_result.get("skipped_attachment_keys", []))
    )
    upload_result["skipped_count"] = skipped_attachment_count or upload_result.get(
        "skipped_count", 0
    )
    return upload_result, all_uploaded_keys


class FeishuBitableRelayAdapter(BaseRelayAdapter):
    def deliver(self, *, event, subscription, delivery) -> RelayAdapterResult:
        handler = FeishuBitableIssueHandler(subscription.config or {})
        plan = (
            (delivery.metadata or {}).get("relay_delivery_plan")
            if hasattr(delivery, "metadata")
            else None
        ) or resolve_delivery_plan(subscription, event, delivery)
        snapshot = event.artifact_snapshot or {}
        title = _apply_feishu_title_prefix(
            subscription,
            snapshot.get("summary_title") or event.email_message.subject,
        )
        issue_data = {
            "title": title,
            "description": snapshot.get("summary_content")
            or snapshot.get("llm_content")
            or "",
            "priority": snapshot.get("priority", "Medium"),
        }
        email_data = {
            "id": str(event.email_message_id),
            "subject": event.email_message.subject,
            "summary_title": title,
            "summary_content": snapshot.get("summary_content") or "",
            "summary_data": snapshot.get("summary_data") or {},
            "llm_content": snapshot.get("llm_content") or "",
            "metadata": snapshot.get("metadata") or {},
            "language": snapshot.get("language") or "en",
            "todos": snapshot.get("todos") or [],
        }
        attachments = snapshot.get("attachments") or []
        if plan["action"] == UPDATE:
            external_id = delivery.external_id or plan["reference_external_id"]
            if external_id:
                try:
                    external_id = handler.update_issue(
                        external_id,
                        issue_data=issue_data,
                        email_data=email_data,
                        attachments=attachments,
                        force=False,
                    )
                except Exception as exc:
                    if not is_missing_issue_error(exc):
                        raise
                    external_id = handler.create_issue(
                        issue_data=issue_data,
                        email_data=email_data,
                        attachments=attachments,
                        force=False,
                    )
            else:
                external_id = handler.create_issue(
                    issue_data=issue_data,
                    email_data=email_data,
                    attachments=attachments,
                    force=False,
                )
        else:
            external_id = handler.create_issue(
                issue_data=issue_data,
                email_data=email_data,
                attachments=attachments,
                force=False,
            )

        link_result = None
        if plan["action"] == NEW_AND_LINK and hasattr(handler, "link_related_issues"):
            link_result = handler.link_related_issues(
                external_id,
                plan["related_issue_keys"],
            )

        metadata = {
            "provider": "feishu_bitable",
            "relay_strategy": plan["action"],
            "relay_strategy_source": plan["source"],
            "relay_related_issue_keys": plan["related_issue_keys"],
            "relay_linking_supported": plan["linking_supported"],
        }
        if link_result is not None:
            metadata["relay_link_result"] = link_result
        metadata["uploaded_attachment_keys"] = []
        metadata["attachment_count"] = len(attachments)

        return RelayAdapterResult(
            external_id=external_id,
            external_url=handler.get_issue_url(external_id),
            metadata=metadata,
        )


class JiraRelayAdapter(BaseRelayAdapter):
    def deliver(self, *, event, subscription, delivery) -> RelayAdapterResult:
        handler = JiraIssueHandler(subscription.config or {})
        plan = (
            (delivery.metadata or {}).get("relay_delivery_plan")
            if hasattr(delivery, "metadata")
            else None
        ) or resolve_delivery_plan(subscription, event, delivery)
        snapshot = event.artifact_snapshot or {}
        issue_data = {
            "title": snapshot.get("summary_title") or event.email_message.subject,
            "description": snapshot.get("summary_content")
            or snapshot.get("llm_content")
            or "",
            "priority": snapshot.get("priority", "Medium"),
        }
        email_data = {
            "id": str(event.email_message_id),
            "subject": event.email_message.subject,
            "summary_title": snapshot.get("summary_title") or event.email_message.subject,
            "summary_content": snapshot.get("summary_content") or "",
            "summary_data": snapshot.get("summary_data") or {},
            "llm_content": snapshot.get("llm_content") or "",
            "metadata": snapshot.get("metadata") or {},
            "language": snapshot.get("language") or "en",
            "todos": snapshot.get("todos") or [],
        }
        attachments = snapshot.get("attachments") or []
        uploaded_attachment_keys: list[str] = []
        if plan["action"] == UPDATE:
            external_id = delivery.external_id or plan["reference_external_id"]
            if external_id:
                try:
                    external_id = handler.update_issue(
                        external_id,
                        summary=issue_data["title"],
                        issue_data=issue_data,
                        email_data=email_data,
                        attachments=attachments,
                        force=False,
                    )
                except Exception as exc:
                    if not is_missing_issue_error(exc):
                        raise
                    external_id = handler.create_issue(
                        issue_data=issue_data,
                        email_data=email_data,
                        attachments=attachments,
                        force=False,
                    )
            else:
                external_id = handler.create_issue(
                    issue_data=issue_data,
                    email_data=email_data,
                    attachments=attachments,
                    force=False,
                )
        else:
            external_id = handler.create_issue(
                issue_data=issue_data,
                email_data=email_data,
                attachments=attachments,
                force=False,
            )

        upload_result, uploaded_attachment_keys = _sync_jira_attachments(
            handler=handler,
            issue_key=external_id,
            attachments=attachments,
            existing_uploaded_keys=_normalize_uploaded_keys(
                (delivery.metadata or {})
            ),
            lookup_remote_uploaded_keys=plan["action"] == UPDATE,
        )

        link_result = None
        if plan["action"] == NEW_AND_LINK:
            link_type = (
                subscription.config.get("jira", {}).get(
                    "issue_link_type", "Relates"
                )
            )
            link_result = handler.link_related_issues(
                external_id,
                plan["related_issue_keys"],
                link_type=link_type,
            )

        metadata = {
            "provider": "jira",
            "relay_strategy": plan["action"],
            "relay_strategy_source": plan["source"],
            "relay_related_issue_keys": plan["related_issue_keys"],
            "relay_linking_supported": plan["linking_supported"],
            "uploaded_attachment_keys": uploaded_attachment_keys,
            "attachment_count": len(attachments),
        }
        if link_result is not None:
            metadata["relay_link_result"] = link_result
        if upload_result is not None:
            metadata["upload_result"] = upload_result

        return RelayAdapterResult(
            external_id=external_id,
            external_url=handler.get_issue_url(external_id),
            metadata=metadata,
        )


class RelayAdapterRegistry:
    _adapters = {
        "feishu_bitable": FeishuBitableRelayAdapter,
        "jira": JiraRelayAdapter,
    }

    @classmethod
    def get_adapter(cls, target_type: str) -> BaseRelayAdapter:
        adapter_cls = cls._adapters.get((target_type or "").strip().lower())
        if not adapter_cls:
            raise ValueError(f"Unsupported relay target type: {target_type}")
        return adapter_cls()
