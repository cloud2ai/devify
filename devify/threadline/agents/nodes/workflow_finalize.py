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

            # Do not sync any data when workflow fails
            # This ensures data consistency: FAILED = no data saved
            # User should use force=true to retry after fixing issues
            issue_result = state.get('issue_result_data')
            if issue_result:
                self.logger.warning(
                    f"Workflow failed but issue was created in "
                    f"external system ({issue_result.get('engine')}): "
                    f"{issue_result.get('external_id')}. "
                    "Issue will NOT be synced to database due to workflow "
                    "errors. Use force=true to retry after fixing issues."
                )

            self.logger.info(
                "Skipping all data sync due to workflow errors"
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

            issue_result = state.get('issue_result_data')
            if issue_result:
                self.logger.info(
                    f"Issue data found in state (engine: "
                    f"{issue_result.get('engine')}), creating Issue record"
                )
                # _create_issue_record will raise exception if it fails
                # No need to check for None - exception will propagate up
                issue = self._create_issue_record(email, issue_result)
                self.logger.info(
                    f"Created Issue record: ID={issue.id}, "
                    f"external_id={issue.external_id}, "
                    f"engine={issue.engine}"
                )

        self.logger.info(
            f"All data synced to database for EmailMessage "
            f"{self.email.id}"
        )

    def _create_issue_record(
        self,
        email: EmailMessage,
        issue_result_data: Dict[str, Any]
    ) -> Issue:
        """
        Create Issue database record from issue engine result data.

        This method is engine-agnostic and handles issue data from
        any supported engine (JIRA, GitHub, Linear, etc.).

        Args:
            email: EmailMessage object
            issue_result_data: Issue result data from State containing:
                - external_id: Issue ID in external system
                - issue_url: Full URL to issue in external system
                - title: Issue title
                - description: Issue description
                - priority: Issue priority
                - engine: Engine type ('jira', 'github', etc.)
                - metadata: Engine-specific metadata

        Returns:
            Created or existing Issue object

        Raises:
            Exception: If Issue creation fails
        """
        engine = issue_result_data.get('engine', 'unknown')
        external_id = issue_result_data.get('external_id')

        self.logger.info(
            f"Creating Issue record with data: "
            f"engine={engine}, "
            f"external_id={external_id}, "
            f"issue_url={issue_result_data.get('issue_url')}, "
            f"title={issue_result_data.get('title', 'Email Issue')[:50]}"
        )

        # Prevent duplicate records for the same external issue
        # Note: An email can have multiple issues, but the same
        # external issue (external_id) should only have one DB record
        if external_id:
            existing_issue = Issue.objects.filter(
                email_message=email,
                external_id=external_id
            ).first()

            if existing_issue:
                self.logger.warning(
                    f"Issue record for {engine} issue {external_id} "
                    f"already exists in database (ID: {existing_issue.id}). "
                    f"Skipping duplicate creation and returning existing record."
                )
                return existing_issue

        # Create new Issue record
        # If this fails, let the exception propagate up
        # It will be caught by BaseLangGraphNode and properly handled
        issue = Issue.objects.create(
            user=email.user,
            email_message=email,
            title=issue_result_data.get('title', 'Email Issue'),
            description=issue_result_data.get(
                'description', 'No content'
            ),
            priority=issue_result_data.get('priority', 'Medium'),
            engine=engine,
            external_id=external_id,
            issue_url=issue_result_data.get('issue_url'),
            metadata={
                'email_id': str(email.id),
                'created_from': 'langgraph_workflow',
                **issue_result_data.get('metadata', {})
            }
        )
        self.logger.info(
            f"Created Issue database record (ID: {issue.id})"
        )
        return issue

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
