"""
Unit tests for merge workflow enqueue behavior.
"""

from unittest.mock import patch

import pytest

from threadline.services.merge_workflow import enqueue_merge_workflow
from threadline.state_machine import EmailStatus

from threadline.tests.integration.helpers import create_threadline_via_api


@pytest.mark.django_db
class TestMergeWorkflow:
    @patch("threadline.tasks.email_merge.process_email_merge.delay")
    def test_enqueue_merge_workflow_marks_target_processing_before_queueing(
        self,
        mock_delay,
        test_user,
    ):
        email = create_threadline_via_api(
            test_user,
            status=EmailStatus.FETCHED.value,
        )

        result = enqueue_merge_workflow(email, trigger_source="api_merge")

        email.refresh_from_db()
        assert result.id == email.id
        assert email.status == EmailStatus.PROCESSING.value
        assert email.metadata["processing_progress"]["percent"] == 0
        mock_delay.assert_called_once_with(
            str(email.id),
            force=False,
            language=None,
            scene=None,
            trigger_source="api_merge",
        )
