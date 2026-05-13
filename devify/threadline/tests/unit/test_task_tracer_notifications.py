from unittest.mock import Mock
from unittest.mock import patch

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


def test_create_task_syncs_initial_zero_progress_snapshot(monkeypatch):
    tracer = TaskTracer("EMAIL_WORKFLOW")
    monkeypatch.setattr(tracer, "_sync_agentcore_registration", Mock())

    fake_message = Mock()
    filter_result = Mock()
    filter_result.only.return_value.first.return_value = fake_message

    with patch(
        "threadline.models.EmailMessage.objects.filter",
        return_value=filter_result,
    ):
        tracer.create_task(
            {
                "email_id": "123",
                "status": "starting",
                "progress_percent": 0,
            }
        )

    fake_message.set_processing_progress.assert_called_once_with(0)


def test_threadline_progress_snapshot_is_monotonic_within_task(monkeypatch):
    tracer = TaskTracer("EMAIL_WORKFLOW")
    tracer._context["email_id"] = "123"

    fake_message = Mock()
    filter_result = Mock()
    filter_result.only.return_value.first.return_value = fake_message

    with patch(
        "threadline.models.EmailMessage.objects.filter",
        return_value=filter_result,
    ):
        tracer._sync_threadline_progress_snapshot(
            {
                "progress_percent": 90,
                "progress_step": "STAGE_A",
            }
        )
        tracer._sync_threadline_progress_snapshot(
            {
                "progress_percent": 78,
                "progress_step": "STAGE_B",
            }
        )

    assert fake_message.set_processing_progress.call_count == 2
    assert fake_message.set_processing_progress.call_args_list[0].args == (92,)
    assert fake_message.set_processing_progress.call_args_list[1].args == (92,)


def test_email_merge_does_not_sync_user_facing_progress(monkeypatch):
    tracer = TaskTracer("EMAIL_MERGE")
    tracer._context["email_id"] = "123"

    fake_message = Mock()
    filter_result = Mock()
    filter_result.only.return_value.first.return_value = fake_message

    with patch(
        "threadline.models.EmailMessage.objects.filter",
        return_value=filter_result,
    ):
        tracer._sync_threadline_progress_snapshot(
            {
                "progress_percent": 75,
                "progress_step": "MERGE_RECONCILE",
            }
        )

    fake_message.set_processing_progress.assert_not_called()
