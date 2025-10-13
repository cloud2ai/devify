"""
Task Tracer Utility

Provides a reusable task tracer for any operations that need to be
tracked in the EmailTask table.

File: devify/threadline/utils/task_tracer.py
"""

import logging
from typing import Dict, Optional

from django.utils import timezone

from threadline.models import EmailTask

logger = logging.getLogger(__name__)


class TaskTracer:
    """
    Task tracer for EmailTask management.

    Handles the creation, updating, and completion of EmailTask records
    for any type of operation. This class can be reused for any task
    that needs to be tracked.

    Example:
        tracer = TaskTracer('HARAKA_CLEANUP')
        tracer.create_task({'task_type': 'HARAKA_CLEANUP'})
        try:
            # Perform task
            tracer.append_task("PROCESS", "Processing...")
            tracer.complete_task(final_details)
        except Exception as e:
            tracer.fail_task(details, str(e))
    """

    def __init__(self, task_type: str):
        """
        Initialize the tracer.

        Args:
            task_type: Type of task (e.g., 'HARAKA_CLEANUP', 'TASK_CLEANUP')
        """
        self.task_type = task_type
        self.task: Optional[EmailTask] = None

    @property
    def task_id(self) -> Optional[int]:
        """Get the task database ID."""
        return self.task.id if self.task else None

    def set_task_id(self, task_id: str) -> None:
        """
        Set Celery task ID.

        Args:
            task_id: Celery task ID
        """
        if not self.task or not task_id:
            return

        try:
            self.task.task_id = task_id
            self.task.save(update_fields=['task_id'])
            logger.debug(f"Set task_id for {self.task_type} task: {task_id}")
        except Exception as e:
            logger.error(f"Failed to set task_id: {e}")



    def create_task(self, initial_details: Dict = None) -> EmailTask:
        """
        Create a task record at the beginning.

        Args:
            initial_details: Initial details for the task

        Returns:
            EmailTask instance or None if creation fails
        """
        try:
            self.task = EmailTask.objects.create(
                task_type=self.task_type,
                status=EmailTask.TaskStatus.RUNNING,
                started_at=timezone.now(),
                details=initial_details or {}
            )
            logger.debug(f"Created {self.task_type} task: {self.task.id}")
            return self.task
        except Exception as e:
            logger.error(f"Failed to create {self.task_type} task: {e}")
            return None

    def update_task(self, details: Dict) -> None:
        """
        Update task with current progress.

        Args:
            details: Updated details dictionary
        """
        if not self.task:
            return

        try:
            self.task.details = details
            self.task.save()
            logger.debug(f"Updated {self.task_type} task: {self.task.id}")
        except Exception as e:
            logger.error(f"Failed to update {self.task_type} task: {e}")

    def complete_task(self, details: Dict) -> None:
        """
        Mark task as completed.

        Args:
            details: Final details dictionary
        """
        if not self.task:
            return

        try:
            self.update_task_status(EmailTask.TaskStatus.COMPLETED)
            self.task.details = details
            self.task.save(update_fields=['details'])
            logger.debug(f"Completed {self.task_type} task: "
                       f"{self.task.id}")
        except Exception as e:
            logger.error(f"Failed to complete {self.task_type} task: {e}")

    def fail_task(self, details: Dict, error_msg: str) -> None:
        """
        Mark task as failed.

        Args:
            details: Current details dictionary
            error_msg: Error message
        """
        if not self.task:
            return

        try:
            self.update_task_status(EmailTask.TaskStatus.FAILED)
            self.task.error_message = error_msg
            details['error'] = error_msg
            details['failed_at'] = timezone.now().isoformat()
            self.task.details = details
            self.task.save(update_fields=['error_message', 'details'])
            logger.debug(f"Marked {self.task_type} task as failed: "
                       f"{self.task.id}")
        except Exception as e:
            logger.error(f"Failed to mark task as failed: {e}")

    def append_task(self, action: str, message: str,
                    data: dict = None) -> None:
        """
        Append task execution log entry.

        Args:
            action: Action type (e.g., 'INIT', 'COMPLETE', 'ERROR')
            message: Log message
            data: Optional additional data
        """
        if not self.task:
            return

        try:
            log_entry = {
                'timestamp': timezone.now().isoformat(),
                'action': action,
                'message': message,
            }
            if data:
                log_entry.update(data)

            if not self.task.details:
                self.task.details = []

            self.task.details.append(log_entry)
            self.task.save(update_fields=['details'])
            logger.debug(f"Appended log to {self.task_type} task: {action}")
        except Exception as e:
            logger.error(f"Failed to append task log: {e}")

    def update_task_status(self, new_status: str) -> None:
        """
        Update task status and timestamps.

        Args:
            new_status: New status to set
        """
        if not self.task:
            return

        try:
            self.task.status = new_status

            # Update timestamps
            if (
                new_status == EmailTask.TaskStatus.RUNNING
                and not self.task.started_at
            ):
                self.task.started_at = timezone.now()
            elif new_status in [
                EmailTask.TaskStatus.COMPLETED,
                EmailTask.TaskStatus.FAILED,
                EmailTask.TaskStatus.CANCELLED,
            ]:
                self.task.completed_at = timezone.now()

            self.task.save()
            logger.debug(f"Updated {self.task_type} task status to: "
                       f"{new_status}")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
