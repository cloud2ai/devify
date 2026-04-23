from unittest.mock import Mock

from threadline.utils.task_tracer import TaskTracer


def test_fail_task_queues_threadline_failure_notification(monkeypatch):
    tracer = TaskTracer("HARAKA_CLEANUP")
    sync_mock = Mock()
    delay_mock = Mock()

    monkeypatch.setattr(tracer, "_sync_agentcore_update", sync_mock)
    monkeypatch.setattr(
        "threadline.tasks.notifications.send_threadline_failure_notification.delay",
        delay_mock,
    )

    tracer.fail_task(
        {
            "cleanup_type": "HARAKA_CLEANUP",
            "errors": 1,
        },
        "boom",
    )

    sync_mock.assert_called_once()
    delay_mock.assert_called_once()
    args = delay_mock.call_args.args
    assert args[0] == "HARAKA_CLEANUP"
    assert args[1]["cleanup_type"] == "HARAKA_CLEANUP"
    assert args[2] == "boom"


def test_append_task_includes_context_and_raw_message(monkeypatch):
    tracer = TaskTracer("EMAIL_WORKFLOW")
    sync_mock = Mock()
    monkeypatch.setattr(tracer, "_sync_agentcore_update", sync_mock)

    tracer.append_task(
        "STEP",
        "Processing email",
        {
            "email_id": 42,
            "user_id": 7,
        },
    )

    sync_mock.assert_called_once()
    entry = tracer._agentcore_metadata["steps"][0]
    assert entry["message"].startswith(
        "[EMAIL_WORKFLOW | email_id=42 user_id=7]"
    )
    assert entry["raw_message"] == "Processing email"
    assert entry["context"]["email_id"] == 42
    assert entry["context"]["user_id"] == 7
