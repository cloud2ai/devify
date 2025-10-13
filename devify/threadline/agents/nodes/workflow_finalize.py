"""
Workflow finalization for email processing.

This node handles the final atomic synchronization of all workflow
results to the database and sets the final processing status.
"""

from typing import Dict, Any

from django.db import transaction

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import (
    EmailState,
    has_node_errors,
    get_all_node_names_with_errors
)
from threadline.models import EmailMessage, EmailAttachment, Issue
from threadline.state_machine import EmailStatus


def _format_node_errors(node_errors: Dict[str, Any]) -> str:
    """
    Format node errors into a readable error message.

    Args:
        node_errors: Dictionary of node errors from state

    Returns:
        Formatted error message string
    """
    error_details = []
    for node_name, errors in node_errors.items():
        for err in errors:
            error_msg = err.get('error_message', 'Unknown error')
            error_details.append(f"{node_name}: {error_msg}")

    return "; ".join(error_details) if error_details else "Unknown errors"


class WorkflowFinalizeNode(BaseLangGraphNode):
    """
    Workflow finalization node for email processing workflow.

    This node serves as the single exit point for all database
    synchronization. It atomically persists all workflow results
    and sets the final processing status based on whether there
    are any node errors.

    Responsibilities:
    - Determine workflow success/failure based on node_errors
    - Atomically sync all workflow results to database
    - Update EmailMessage status to SUCCESS or FAILED
    - Sync attachment OCR/LLM results
    - Sync issue results from State
    - Handle force mode considerations
    - Ensure data consistency and integrity

    Note: This node ONLY syncs data, it does NOT create issues.
    Issue creation is handled by IssueNode.
    """

    def __init__(self):
        super().__init__("workflow_finalize_node")
        self.email = None

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Finalize node always runs to ensure proper cleanup.
        """
        return True

    def before_processing(self, state: EmailState) -> EmailState:
        """
        Pre-processing: Basic validation for finalization.

        Args:
            state: Current email state

        Returns:
            EmailState: Validated state
        """
        email_id = state.get('id')
        if not email_id:
            raise ValueError('email_id is required for finalization')

        try:
            self.email = EmailMessage.objects.get(id=email_id)
        except EmailMessage.DoesNotExist:
            raise ValueError(f'EmailMessage {email_id} not found')

        self.logger.info(
            f"Starting finalization for EmailMessage {email_id}"
        )
        return state

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute database operations and status update based on
        workflow results.

        1. Determine workflow success/failure based on node_errors
        2. If successful: sync data to database and set SUCCESS status
        3. If failed: only set FAILED status, no data sync
        """
        has_errors = has_node_errors(state)
        force = state.get('force', False)

        if has_errors:
            error_nodes = get_all_node_names_with_errors(state)
            node_errors = state.get('node_errors', {})
            error_summary = _format_node_errors(node_errors)

            self.logger.error(
                f"Workflow failed with errors in nodes: {error_nodes}"
            )
            self.logger.info(
                "Skipping data sync due to workflow errors"
            )

            if not force:
                self.email.set_status(
                    EmailStatus.FAILED.value,
                    error_message=error_summary
                )
                self.logger.info(
                    f"EmailMessage {self.email.id} status set to FAILED"
                )
            else:
                self.logger.info(
                    f"Force mode: skipping status update to FAILED, "
                    f"current status remains {self.email.status}"
                )
        else:
            self.logger.info("Workflow completed successfully")

            self._sync_data_to_database(state)

            if not force:
                self.email.set_status(EmailStatus.SUCCESS.value)
                self.logger.info(
                    f"EmailMessage {self.email.id} status set to SUCCESS"
                )
            else:
                self.logger.info(
                    f"Force mode: skipping status update to SUCCESS, "
                    f"current status remains {self.email.status}"
                )

        self.logger.info(
            f"Workflow finalized for EmailMessage {self.email.id}"
        )
        return state

    def _sync_data_to_database(self, state: EmailState) -> None:
        """
        Sync all workflow results to database atomically.

        This method handles all data updates but does NOT update status.
        Status updates are handled separately in execute_processing.

        Args:
            state: Current email state
        """
        with transaction.atomic():
            email = EmailMessage.objects.select_for_update().get(
                id=self.email.id
            )

            update_fields = []

            summary_title = state.get('summary_title', '')
            if summary_title:
                email.summary_title = summary_title
                update_fields.append('summary_title')
                self.logger.info("Synced summary_title to database")

            summary_content = state.get('summary_content', '')
            if summary_content:
                email.summary_content = summary_content
                update_fields.append('summary_content')
                self.logger.info("Synced summary_content to database")

            llm_content = state.get('llm_content', '')
            if llm_content:
                email.llm_content = llm_content
                update_fields.append('llm_content')
                self.logger.info("Synced llm_content to database")

            if update_fields:
                email.save(update_fields=update_fields)
                self.logger.info(
                    f"EmailMessage {self.email.id} saved to database "
                    f"with fields: {update_fields}"
                )

            attachments = state.get('attachments', [])
            if attachments:
                for att_data in attachments:
                    att_id = att_data.get('id')
                    if not att_id:
                        continue

                    att_update_fields = []
                    att_updates = {}

                    ocr_content = att_data.get('ocr_content')
                    if ocr_content:
                        att_updates['ocr_content'] = ocr_content
                        att_update_fields.append('ocr_content')

                    llm_content = att_data.get('llm_content')
                    if llm_content:
                        att_updates['llm_content'] = llm_content
                        att_update_fields.append('llm_content')

                    if att_updates:
                        EmailAttachment.objects.filter(
                            id=att_id
                        ).update(**att_updates)
                        self.logger.info(
                            f"Synced attachment {att_id} fields: "
                            f"{att_update_fields}"
                        )

            jira_issue_data = state.get('jira_issue_data')
            if jira_issue_data:
                self.logger.info(
                    f"JIRA issue data found in state, creating Issue record"
                )
                issue = self._create_issue_record(email, jira_issue_data)
                if issue:
                    self.logger.info(
                        f"Created Issue record: ID={issue.id}, "
                        f"external_id={issue.external_id}"
                    )
                else:
                    self.logger.warning(
                        "Failed to create Issue database record"
                    )

        self.logger.info(
            f"All data synced to database for EmailMessage "
            f"{self.email.id}"
        )

    def _create_issue_record(
        self,
        email: EmailMessage,
        jira_issue_data: Dict[str, Any]
    ) -> Issue | None:
        """
        Create Issue database record from JIRA issue data.

        This method creates the Issue database record based on
        JIRA API results stored in State by IssueNode.

        Args:
            email: EmailMessage object
            jira_issue_data: JIRA issue data from State containing:
                - issue_key: JIRA issue key
                - issue_url: Full URL to JIRA issue
                - title: Issue title
                - description: Issue description
                - priority: Issue priority
                - upload_result: Attachment upload result

        Returns:
            Created Issue object, or None if creation failed
        """
        try:
            issue = Issue.objects.create(
                user=email.user,
                email_message=email,
                title=jira_issue_data.get('title', 'Email Issue'),
                description=jira_issue_data.get(
                    'description', 'No content'
                ),
                priority=jira_issue_data.get('priority', 'Medium'),
                engine=jira_issue_data.get('engine', 'jira'),
                external_id=jira_issue_data.get('issue_key'),
                issue_url=jira_issue_data.get('issue_url'),
                metadata={
                    'email_id': str(email.id),
                    'created_from': 'langgraph_workflow',
                    'jira_project': jira_issue_data.get('project'),
                    'upload_result': jira_issue_data.get('upload_result')
                }
            )
            self.logger.info(
                f"Created Issue database record (ID: {issue.id})"
            )
            return issue

        except Exception as e:
            self.logger.error(f"Failed to create Issue record: {e}")
            return None

    def _handle_error(
        self, error: Exception, state: EmailState
    ) -> EmailState:
        """
        Handle errors that occur during finalization processing.

        For finalize node, we need to ensure the database status is
        updated even if the finalization process itself fails.

        Args:
            error: The error that occurred
            state: Current email state

        Returns:
            EmailState: Updated state with error information
        """
        state = super()._handle_error(error, state)

        force = state.get('force', False)
        if force:
            self.logger.info(
                "Force mode: skipping status update after "
                "finalization error"
            )
            return state

        try:
            node_errors = state.get('node_errors', {})
            error_summary = _format_node_errors(node_errors)
            error_message = f"Finalization failed - {error_summary}"

            self.email.set_status(
                EmailStatus.FAILED.value,
                error_message=error_message
            )
            self.logger.info(
                f"EmailMessage {self.email.id} status set to FAILED "
                f"due to finalization error"
            )
        except Exception as status_error:
            self.logger.error(
                f"Failed to update status after finalization error: "
                f"{status_error}"
            )

        return state
