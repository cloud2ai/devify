"""Threadline failure notification helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from celery import shared_task
from django.utils import timezone
from agentcore_notifier.adapters.django.models import NotificationChannel
from agentcore_notifier.constants import Provider
from agentcore_notifier.adapters.django.tasks.send import (
    send_webhook_notification as agentcore_send_webhook_notification,
)

from threadline.models import EmailMessage
from threadline.services.workflow_config import (
    resolve_threadline_notification_channel,
)

logger = logging.getLogger(__name__)

THREADLINE_SOURCE_APP = "threadline"
DEFAULT_NOTIFICATION_LANGUAGE = "zh-hans"

NOTIFICATION_COPY = {
    "zh-hans": {
        "email_title": "【Threadline】邮件处理失败",
        "task_title": "【Threadline】任务失败",
        "card_title": "线程失败通知",
        "fields": {
            "time": "时间",
            "email_id": "邮件ID",
            "subject": "主题",
            "sender": "发件人",
            "previous_status": "前一状态",
            "current_status": "当前状态",
            "task_type": "任务类型",
            "task_id": "任务ID",
            "user_id": "用户ID",
            "cleanup_type": "清理类型",
            "scene": "场景",
            "language": "语言",
            "workflow_error": "流程错误",
            "error_count": "错误数",
            "tasks_cleaned": "已清理任务数",
            "links_deactivated": "已失效链接数",
            "error": "错误",
        },
    },
    "en": {
        "email_title": "[Threadline] Email processing failed",
        "task_title": "[Threadline] Task failed",
        "card_title": "Threadline Failure Notification",
        "fields": {
            "time": "Time",
            "email_id": "Email ID",
            "subject": "Subject",
            "sender": "Sender",
            "previous_status": "Previous status",
            "current_status": "Current status",
            "task_type": "Task type",
            "task_id": "Task ID",
            "user_id": "User ID",
            "cleanup_type": "Cleanup type",
            "scene": "Scene",
            "language": "Language",
            "workflow_error": "Workflow error",
            "error_count": "Error count",
            "tasks_cleaned": "Tasks cleaned",
            "links_deactivated": "Links deactivated",
            "error": "Error",
        },
    },
}


def _normalize_notification_language(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_NOTIFICATION_LANGUAGE
    normalized = str(language).strip().lower()
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("zh"):
        return "zh-hans"
    return DEFAULT_NOTIFICATION_LANGUAGE


def _get_notification_copy(language: Optional[str]) -> Dict[str, Any]:
    normalized = _normalize_notification_language(language)
    return NOTIFICATION_COPY.get(
        normalized,
        NOTIFICATION_COPY[DEFAULT_NOTIFICATION_LANGUAGE],
    )


def _normalize_markdown_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().replace("\n", " ")
    return str(value).strip()


def _build_markdown_bullet_list(items: Dict[str, Any]) -> str:
    lines = []
    for label, value in items.items():
        normalized = _normalize_markdown_value(value)
        if not normalized:
            continue
        lines.append(f"- **{label}**: {normalized}")
    return "\n".join(lines)


def _build_feishu_interactive_card(
    title: str,
    markdown: str,
    message_prefix: str = "",
) -> Dict[str, Any]:
    full_title = (
        f"{message_prefix} {title}".strip() if message_prefix else title
    )
    return {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": full_title,
                },
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": markdown,
                    },
                }
            ],
        },
    }


def _resolve_webhook_notification_channel() -> (
    tuple[object | None, dict | None]
):
    channel = resolve_threadline_notification_channel()
    if not channel:
        return None, None
    if channel.channel_type != NotificationChannel.TYPE_WEBHOOK:
        logger.warning(
            f"Threadline notification channel {channel.uuid} is not "
            "webhook; skipping"
        )
        return None, None

    config = channel.config or {}
    provider_type = (
        config.get("provider_type") or config.get("provider") or "feishu"
    )
    provider_type = str(provider_type).strip().lower() or "feishu"
    return channel, {
        "provider_type": provider_type,
        "message_prefix": (config.get("message_prefix") or "").strip(),
        "language": _normalize_notification_language(config.get("language")),
    }


def build_email_failure_text(
    email: EmailMessage,
    old_status: str,
    new_status: str,
    language: Optional[str] = None,
) -> str:
    """
    Build a markdown failure summary for an email status transition.
    """
    copy = _get_notification_copy(language)
    details = _build_markdown_bullet_list(
        {
            copy["fields"]["time"]: timezone.now().isoformat(),
            copy["fields"]["email_id"]: email.id,
            copy["fields"]["subject"]: email.subject,
            copy["fields"]["sender"]: email.sender,
            copy["fields"]["previous_status"]: old_status,
            copy["fields"]["current_status"]: new_status,
            copy["fields"]["error"]: email.error_message or None,
        }
    )
    message = copy["email_title"]
    return f"**{message}**\n\n{details}" if details else f"**{message}**"


def build_task_failure_text(
    task_type: str,
    details: Optional[Dict[str, Any]],
    error_msg: str,
    language: Optional[str] = None,
) -> str:
    """
    Build a markdown failure summary for a background task.
    """
    payload = details or {}
    copy = _get_notification_copy(language)
    summary = _build_markdown_bullet_list(
        {
            copy["fields"]["time"]: timezone.now().isoformat(),
            copy["fields"]["task_type"]: task_type,
            copy["fields"]["task_id"]: payload.get("task_id"),
            copy["fields"]["email_id"]: payload.get("email_id"),
            copy["fields"]["user_id"]: payload.get("user_id"),
            copy["fields"]["cleanup_type"]: payload.get("cleanup_type"),
            copy["fields"]["scene"]: payload.get("scene"),
            copy["fields"]["language"]: payload.get("language"),
            copy["fields"]["workflow_error"]: payload.get("workflow_error"),
            copy["fields"]["error_count"]: payload.get("error_count"),
            copy["fields"]["tasks_cleaned"]: payload.get("tasks_cleaned"),
            copy["fields"]["links_deactivated"]: payload.get(
                "links_deactivated"
            ),
            copy["fields"]["error"]: error_msg,
        }
    )
    return (
        f"**{copy['task_title']}**\n\n{summary}"
        if summary
        else f"**{copy['task_title']}**"
    )


def _queue_webhook_notification(
    text: str,
    source_type: str,
    source_id: str,
    user_id: Optional[int] = None,
):
    channel, channel_config = _resolve_webhook_notification_channel()
    if not channel or not channel_config:
        logger.warning(
            "Threadline notification channel is unavailable; skipping"
        )
        return None

    provider_type = channel_config["provider_type"]
    if str(provider_type).strip().lower() != Provider.FEISHU:
        logger.warning(
            f"Unsupported Threadline notification provider_type="
            f"{provider_type}; skipping notification"
        )
        return None
    message_prefix = channel_config.get("message_prefix", "")
    language = channel_config.get("language", DEFAULT_NOTIFICATION_LANGUAGE)
    payload = _build_feishu_interactive_card(
        _get_notification_copy(language)["card_title"],
        text,
        message_prefix=message_prefix,
    )
    return agentcore_send_webhook_notification.delay(
        payload=payload,
        provider_type=provider_type,
        source_app=THREADLINE_SOURCE_APP,
        source_type=source_type,
        source_id=source_id,
        user_id=user_id,
        channel_uuid=str(channel.uuid),
    )


@shared_task(bind=True, max_retries=3)
def send_threadline_notification(
    self,
    text: str,
    source_type: str,
    source_id: str,
    user_id: Optional[int] = None,
):
    """
    Queue a threadline failure notification through the configured channel.
    """
    try:
        return _queue_webhook_notification(
            text=text,
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
        )
    except Exception as exc:
        logger.error(f"Threadline notification failed: {exc}")
        self.retry(countdown=60, exc=exc)


@shared_task(bind=True, max_retries=3)
def send_threadline_failure_notification(
    self,
    task_type: str,
    details: Optional[Dict[str, Any]],
    error_msg: str,
    user_id: Optional[int] = None,
):
    """
    Build and queue a threadline failure notification.
    """
    try:
        _channel, channel_config = _resolve_webhook_notification_channel()
        language = (
            channel_config.get("language")
            if channel_config
            else DEFAULT_NOTIFICATION_LANGUAGE
        )
        text = build_task_failure_text(
            task_type,
            details,
            error_msg,
            language=language,
        )
        source_id = str(
            (details or {}).get("email_id")
            or (details or {}).get("task_id")
            or task_type
        )
        resolved_user_id = (
            user_id
            if user_id is not None
            else ((details or {}).get("user_id"))
        )
        return _queue_webhook_notification(
            text=text,
            source_type=task_type,
            source_id=source_id,
            user_id=resolved_user_id,
        )
    except Exception as exc:
        logger.error(f"Threadline failure notification failed: {exc}")
        self.retry(countdown=60, exc=exc)
