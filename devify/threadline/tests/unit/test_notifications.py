from types import SimpleNamespace
from uuid import uuid4

from unittest.mock import Mock

from threadline.tasks.notifications import (
    build_email_failure_text,
    send_threadline_notification,
)


def test_build_email_failure_text_includes_key_fields():
    email = SimpleNamespace(
        id=42,
        subject="Hello",
        sender="sender@example.com",
        error_message="boom",
    )

    text = build_email_failure_text(email, "processing", "failed")

    assert "【Threadline】邮件处理失败" in text
    assert "- **邮件ID**: 42" in text
    assert "- **主题**: Hello" in text
    assert "- **发件人**: sender@example.com" in text
    assert "- **前一状态**: processing" in text
    assert "- **当前状态**: failed" in text
    assert "- **错误**: boom" in text


def test_build_email_failure_text_uses_english_language():
    email = SimpleNamespace(
        id=7,
        subject="Hello",
        sender="sender@example.com",
        error_message="boom",
    )

    text = build_email_failure_text(email, "processing", "failed", "en")

    assert "[Threadline] Email processing failed" in text
    assert "- **Email ID**: 7" in text
    assert "- **Subject**: Hello" in text
    assert "- **Sender**: sender@example.com" in text
    assert "- **Previous status**: processing" in text
    assert "- **Current status**: failed" in text
    assert "- **Error**: boom" in text


def test_send_threadline_notification_queues_agentcore_task(monkeypatch):
    channel_uuid = uuid4()
    channel = SimpleNamespace(
        uuid=channel_uuid,
        channel_type="webhook",
        config={
            "provider_type": "feishu",
            "message_prefix": "[测试消息]",
            "language": "en",
        },
    )
    delay_mock = Mock(return_value={"queued": True})

    monkeypatch.setattr(
        "threadline.tasks.notifications.resolve_threadline_notification_channel",
        lambda: channel,
    )
    monkeypatch.setattr(
        "threadline.tasks.notifications.agentcore_send_webhook_notification.delay",
        delay_mock,
    )

    result = send_threadline_notification.run(
        "failure text",
        "manual_test",
        "email:42",
        user_id=7,
    )

    assert result == {"queued": True}
    delay_mock.assert_called_once()
    kwargs = delay_mock.call_args.kwargs
    assert kwargs["provider_type"] == "feishu"
    assert kwargs["source_app"] == "threadline"
    assert kwargs["source_type"] == "manual_test"
    assert kwargs["source_id"] == "email:42"
    assert kwargs["user_id"] == 7
    assert kwargs["channel_uuid"] == str(channel_uuid)
    assert kwargs["payload"]["msg_type"] == "interactive"
    assert kwargs["payload"]["card"]["header"]["title"]["content"] == (
        "[测试消息] Threadline Failure Notification"
    )
    assert kwargs["payload"]["card"]["elements"][0]["text"]["content"] == (
        "failure text"
    )


def test_send_threadline_notification_skips_unsupported_provider(monkeypatch):
    channel_uuid = uuid4()
    channel = SimpleNamespace(
        uuid=channel_uuid,
        channel_type="webhook",
        config={
            "provider_type": "wechat",
            "message_prefix": "[测试消息]",
            "language": "en",
        },
    )
    delay_mock = Mock()

    monkeypatch.setattr(
        "threadline.tasks.notifications.resolve_threadline_notification_channel",
        lambda: channel,
    )
    monkeypatch.setattr(
        "threadline.tasks.notifications.agentcore_send_webhook_notification.delay",
        delay_mock,
    )

    result = send_threadline_notification.run(
        "failure text",
        "manual_test",
        "email:42",
        user_id=7,
    )

    assert result is None
    delay_mock.assert_not_called()
