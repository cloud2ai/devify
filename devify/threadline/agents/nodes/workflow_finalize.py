"""
Workflow finalization for email processing.

This node handles the final atomic synchronization of all workflow
results to the database and sets the final processing status.
"""

import logging
from typing import Dict, Any

from django.db import transaction

logger = logging.getLogger(__name__)

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

        user_id = state.get('user_id')
        logger.info(
            f"[{self.node_name}] Starting finalization for "
            f"email {email_id}, user {user_id}"
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

            logger.error(
                f"Workflow failed with errors in nodes: {error_nodes}"
            )

            # Do not sync any data when workflow fails
            # This ensures data consistency: FAILED = no data saved
            # User should use force=true to retry after fixing issues
            issue_result = state.get('issue_result_data')
            if issue_result:
                logger.warning(
                    f"Workflow failed but issue was created in "
                    f"external system ({issue_result.get('engine')}): "
                    f"{issue_result.get('external_id')}. "
                    "Issue will NOT be synced to database due to workflow "
                    "errors. Use force=true to retry after fixing issues."
                )

            logger.info(
                "Skipping all data sync due to workflow errors"
            )

            if not force:
                self.email.set_status(
                    EmailStatus.FAILED.value,
                    error_message=error_summary
                )
                logger.info(
                    f"EmailMessage {self.email.id} status set to FAILED"
                )
            else:
                logger.info(
                    f"Force mode: skipping status update to FAILED, "
                    f"current status remains {self.email.status}"
                )
        else:
            email_id = state.get('id')
            user_id = state.get('user_id')
            logger.info(
                f"[{self.node_name}] Workflow completed successfully for "
                f"email {email_id}, user {user_id}"
            )

            self._sync_data_to_database(state)

            if not force:
                self.email.set_status(EmailStatus.SUCCESS.value)
                logger.info(
                    f"[{self.node_name}] Status set to SUCCESS for "
                    f"email {self.email.id}, user {user_id}"
                )
            else:
                logger.info(
                    f"Force mode: skipping status update for "
                    f"email {self.email.id}, status remains "
                    f"{self.email.status}"
                )

        email_id = state.get('id')
        user_id = state.get('user_id')
        logger.info(
            f"[{self.node_name}] Workflow finalized for "
            f"email {email_id}, user {user_id}"
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

            field_updates = {
                'summary_title': state.get('summary_title', ''),
                'summary_content': state.get('summary_content', ''),
                'llm_content': state.get('llm_content', ''),
                'metadata': state.get('metadata')
            }

            update_fields = []
            sync_details = []

            for field_name, field_value in field_updates.items():
                if not field_value:
                    continue

                setattr(email, field_name, field_value)
                update_fields.append(field_name)

                if isinstance(field_value, dict):
                    detail = f"{field_name}({len(field_value)} keys)"
                    logger.debug(
                        f"{field_name}: {list(field_value.keys())}"
                    )
                else:
                    detail = f"{field_name}({len(field_value)} chars)"
                    logger.debug(
                        f"{field_name}: {str(field_value)[:100]}"
                    )
                sync_details.append(detail)

            if update_fields:
                logger.debug(
                    f"Saving EmailMessage {self.email.id} "
                    f"with fields: {update_fields}"
                )
                email.save(update_fields=update_fields)
                logger.info(
                    f"Synced EmailMessage {self.email.id}: "
                    f"{', '.join(sync_details)}"
                )

            attachments = state.get('attachments', [])
            if attachments:
                att_sync_count = 0
                att_sync_summary = []

                for att_data in attachments:
                    att_id = att_data.get('id')
                    if not att_id:
                        continue

                    att_field_updates = {
                        'ocr_content': att_data.get('ocr_content'),
                        'llm_content': att_data.get('llm_content')
                    }

                    att_updates = {}
                    att_details = []

                    for field_name, field_value in (
                        att_field_updates.items()
                    ):
                        if not field_value:
                            continue

                        att_updates[field_name] = field_value
                        field_type = field_name.split('_')[0]
                        att_details.append(
                            f"{field_type}({len(field_value)} chars)"
                        )
                        logger.debug(
                            f"Attachment {att_id} {field_name}: "
                            f"{field_value[:100]}"
                        )

                    if att_updates:
                        logger.debug(
                            f"Updating attachment {att_id} "
                            f"with fields: {list(att_updates.keys())}"
                        )
                        EmailAttachment.objects.filter(
                            id=att_id
                        ).update(**att_updates)
                        att_sync_count += 1
                        att_sync_summary.append(
                            f"#{att_id}[{', '.join(att_details)}]"
                        )

                if att_sync_count > 0:
                    logger.info(
                        f"Synced {att_sync_count} attachment(s): "
                        f"{', '.join(att_sync_summary)}"
                    )

            issue_result = state.get('issue_result_data')
            if issue_result:
                issue = self._create_issue_record(email, issue_result)
                logger.info(
                    f"Created Issue: "
                    f"ID={issue.id}, "
                    f"engine={issue.engine}, "
                    f"external_id={issue.external_id}, "
                    f"url={issue.issue_url}"
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
        title = issue_result_data.get('title', 'Email Issue')

        logger.debug(
            f"Creating Issue record: "
            f"engine={engine}, "
            f"external_id={external_id}, "
            f"title={title[:50]}"
        )

        if external_id:
            existing_issue = Issue.objects.filter(
                email_message=email,
                external_id=external_id
            ).first()

            if existing_issue:
                logger.info(
                    f"Issue already exists: "
                    f"ID={existing_issue.id}, "
                    f"external_id={external_id}"
                )
                return existing_issue

        issue = Issue.objects.create(
            user=email.user,
            email_message=email,
            title=title,
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
            logger.info(
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
            logger.info(
                f"EmailMessage {self.email.id} status set to FAILED "
                f"due to finalization error"
            )
        except Exception as status_error:
            logger.error(
                f"Failed to update status after finalization error: "
                f"{status_error}"
            )

        return state
