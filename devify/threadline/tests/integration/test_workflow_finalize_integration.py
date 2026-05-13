"""
Integration tests for workflow finalization and database sync.
"""

from unittest.mock import patch

import pytest

from threadline.agents.nodes.workflow_finalize import WorkflowFinalizeNode
from threadline.models import EmailTodo, Issue
from threadline.state_machine import EmailStatus

from ..fixtures.email_scenarios import (
    build_workflow_finalize_state,
    create_email_message_scenario,
)


@pytest.mark.django_db
@pytest.mark.integration
class TestWorkflowFinalizeIntegration:
    def test_finalize_success_syncs_email_todo_attachment_and_issue(
        self, test_user
    ):
        scenario = create_email_message_scenario(
            test_user,
            subject="Workflow subject",
            status=EmailStatus.PROCESSING.value,
            text_content="Workflow source body",
            attachments=[
                {
                    "filename": "workflow.pdf",
                    "safe_filename": "workflow.pdf",
                    "content_type": "application/pdf",
                    "file_size": 4096,
                    "file_path": "/uploads/workflow.pdf",
                    "is_image": False,
                }
            ],
        )
        email = scenario.email
        attachment = scenario.attachments[0]

        node = WorkflowFinalizeNode()
        node.email = email

        with patch(
            "threadline.agents.nodes.workflow_finalize.settings.ENABLE_COST_TRACKING",
            False,
        ), patch.object(
            WorkflowFinalizeNode, "_record_progress_step", lambda *args, **kwargs: None
        ):
            node.execute_processing(
                build_workflow_finalize_state(email, force=True)
            )

        email.refresh_from_db()
        attachment.refresh_from_db()

        assert email.status == EmailStatus.SUCCESS.value
        assert email.summary_title == "Resolved summary title"
        assert email.summary_content == "Resolved summary content"
        assert email.llm_content == "Resolved llm content"
        assert email.metadata == {"keywords": ["alpha"]}
        assert attachment.ocr_content == "OCR body"
        assert attachment.llm_content == "LLM body"

        todo = EmailTodo.objects.get(email_message=email)
        assert todo.content == "Follow up with customer"
        assert todo.priority == "high"
        assert todo.owner == "Alice"
        assert todo.location == "Shanghai"
        assert todo.metadata == {"source": "workflow"}
        assert todo.deadline is not None

        issue = Issue.objects.get(email_message=email, external_id="REQ-900")
        assert issue.title == "Resolved summary title"
        assert issue.description == "Resolved summary content"
        assert issue.priority == "High"
        assert issue.metadata["email_id"] == str(email.id)
        assert issue.metadata["created_from"] == "langgraph_workflow"
        assert issue.metadata["provider"] == "jira"

    def test_finalize_failed_syncs_partial_data_and_updates_issue(
        self, test_user
    ):
        scenario = create_email_message_scenario(
            test_user,
            subject="Workflow subject",
            status=EmailStatus.PROCESSING.value,
            text_content="Workflow source body",
            attachments=[
                {
                    "filename": "workflow.pdf",
                    "safe_filename": "workflow.pdf",
                    "content_type": "application/pdf",
                    "file_size": 4096,
                    "file_path": "/uploads/workflow.pdf",
                    "is_image": False,
                }
            ],
        )
        email = scenario.email
        attachment = scenario.attachments[0]
        existing_issue = Issue.objects.create(
            user=test_user,
            email_message=email,
            title="Original title",
            description="Original description",
            priority="Medium",
            engine="jira",
            external_id="REQ-900",
            issue_url="https://jira.example.com/browse/REQ-900",
            metadata={"seeded": True},
        )

        node = WorkflowFinalizeNode()
        node.email = email

        state = build_workflow_finalize_state(
            email,
            issue_id=existing_issue.id,
            force=True,
            node_errors={
                "summary": [
                    {
                        "error_message": "summary generation failed",
                        "timestamp": "2026-05-07T09:00:00Z",
                    }
                ]
            },
            issue_result_data={
                "external_id": "REQ-900",
                "issue_url": "https://jira.example.com/browse/REQ-900",
                "title": "Recovered title",
                "description": "Recovered description",
                "priority": "High",
                "engine": "jira",
                "metadata": {"provider": "jira", "mode": "retry"},
            },
        )

        with patch(
            "threadline.agents.nodes.workflow_finalize.settings.ENABLE_COST_TRACKING",
            False,
        ), patch.object(
            WorkflowFinalizeNode, "_record_progress_step", lambda *args, **kwargs: None
        ):
            node.execute_processing(state)

        email.refresh_from_db()
        attachment.refresh_from_db()
        existing_issue.refresh_from_db()

        assert email.status == EmailStatus.FAILED.value
        assert "summary generation failed" in email.error_message
        assert email.summary_title == "Resolved summary title"
        assert email.summary_content == "Resolved summary content"
        assert attachment.ocr_content == "OCR body"
        assert attachment.llm_content == "LLM body"

        assert existing_issue.title == "Recovered title"
        assert existing_issue.description == "Recovered description"
        assert existing_issue.priority == "High"
        assert existing_issue.metadata["seeded"] is True
        assert existing_issue.metadata["provider"] == "jira"
        assert existing_issue.metadata["mode"] == "retry"
