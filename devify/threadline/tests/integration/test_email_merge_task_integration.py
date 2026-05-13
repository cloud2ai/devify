"""
Integration tests for email merge task dispatch.
"""

from unittest.mock import patch

import pytest

from threadline.state_machine import EmailStatus
from threadline.tasks.email_merge import process_email_merge

from .helpers import create_threadline_via_api


@pytest.mark.django_db
@pytest.mark.integration
class TestEmailMergeTaskIntegration:
    @patch(
        "agentcore_task.adapters.django.services.lock.release_task_lock",
        return_value=True,
    )
    @patch(
        "agentcore_task.adapters.django.services.lock.acquire_task_lock",
        return_value=True,
    )
    @patch(
        "agentcore_task.adapters.django.services.lock.is_task_locked",
        return_value=False,
    )
    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    def test_process_email_merge_dispatches_workflow_with_force_flag(
        self,
        mock_delay,
        mock_is_locked,
        mock_acquire_lock,
        mock_release_lock,
        test_user,
    ):
        email = create_threadline_via_api(
            user=test_user,
            status=EmailStatus.FETCHED.value,
        )

        result = process_email_merge(
            str(email.id),
            force=True,
            language="zh-CN",
            scene="product_issue",
            trigger_source="retry_task",
        )

        assert result == str(email.id)
        mock_delay.assert_called_once_with(
            str(email.id),
            force=True,
            language="zh-CN",
            scene="product_issue",
            trigger_source="retry_task",
        )

    @patch(
        "agentcore_task.adapters.django.services.lock.release_task_lock",
        return_value=True,
    )
    @patch(
        "agentcore_task.adapters.django.services.lock.acquire_task_lock",
        return_value=True,
    )
    @patch(
        "agentcore_task.adapters.django.services.lock.is_task_locked",
        return_value=False,
    )
    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    def test_process_email_merge_marks_failed_when_dispatch_raises(
        self,
        mock_delay,
        mock_is_locked,
        mock_acquire_lock,
        mock_release_lock,
        test_user,
    ):
        email = create_threadline_via_api(
            user=test_user,
            status=EmailStatus.FETCHED.value,
        )
        mock_delay.side_effect = RuntimeError("broker down")

        with pytest.raises(RuntimeError, match="broker down"):
            process_email_merge(str(email.id))

        email.refresh_from_db()
        assert email.status == EmailStatus.FAILED.value
        assert "broker down" in email.error_message
