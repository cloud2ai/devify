"""
Task Tracer Utility

Dual-writes task execution state to the legacy EmailTask model and to
agentcore-task's TaskExecution records. This keeps existing code paths and
tests stable while moving task management to agentcore.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from uuid import uuid4
from typing import Dict, Optional

from celery import current_task
from django.utils import timezone

from threadline.models import EmailTask

logger = logging.getLogger(__name__)
_current_task_tracer: ContextVar["TaskTracer | None"] = ContextVar(
    "current_task_tracer",
    default=None,
)


def _normalize_metadata(details) -> Dict:
    if isinstance(details, dict):
        return deepcopy(details)
    if details is None:
        return {}
    return {"details": deepcopy(details)}


_CONTEXT_KEYS = (
    "email_id",
    "user_id",
    "task_id",
    "cleanup_type",
    "source_type",
    "source_id",
    "scene",
    "language",
    "status",
    "force",
)


def _current_celery_task_id() -> Optional[str]:
    try:
        request = getattr(current_task, "request", None)
        task_id = getattr(request, "id", None)
        if task_id:
            return str(task_id)
    except Exception:
        pass
    return None


def get_current_task_tracer() -> "TaskTracer | None":
    return _current_task_tracer.get()


@contextmanager
def use_task_tracer(tracer: "TaskTracer"):
    token = _current_task_tracer.set(tracer)
    try:
        yield tracer
    finally:
        _current_task_tracer.reset(token)


class TaskTracer:
    """
    Task tracer for EmailTask management plus agentcore shadow records.
    """

    def __init__(
        self,
        task_type: str,
        module: str = "threadline",
        track_legacy: bool = True,
    ):
        self.task_type = task_type
        self.module = module
        self.track_legacy = track_legacy
        self.task: Optional[EmailTask] = None
        self._task_id: Optional[str] = None
        self._agentcore_task_id: Optional[str] = None
        self._agentcore_metadata: Dict = {}
        self._context: Dict[str, object] = {}

    @property
    def task_id(self) -> Optional[int]:
        return self.task.id if self.task else None

    def _ensure_agentcore_imports(self):
        from agentcore_task.adapters.django import (
            TaskStatus,
            TaskTracker,
            register_task_execution,
        )

        return TaskStatus, TaskTracker, register_task_execution

    def _sync_agentcore_registration(self, initial_details: Dict = None):
        TaskStatus, _, register_task_execution = (
            self._ensure_agentcore_imports()
        )

        if self._agentcore_task_id:
            return

        try:
            task_id = (
                self._task_id or _current_celery_task_id() or str(uuid4())
            )
            self._agentcore_task_id = task_id
            self._agentcore_metadata = _normalize_metadata(initial_details)
            self._merge_context(initial_details)
            register_task_execution(
                task_id=task_id,
                task_name=self.task_type,
                module=self.module,
                task_args=[],
                task_kwargs={},
                metadata=self._agentcore_metadata,
                initial_status=TaskStatus.STARTED,
            )
        except Exception as exc:
            logger.debug(f"Failed to seed agentcore task record: {exc}")

    def _sync_agentcore_update(
        self,
        status: str,
        *,
        result=None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        TaskStatus, TaskTracker, _ = self._ensure_agentcore_imports()
        if not self._agentcore_task_id:
            self._sync_agentcore_registration(metadata)

        if metadata:
            self._agentcore_metadata.update(_normalize_metadata(metadata))

        try:
            TaskTracker.update_task_status(
                task_id=self._agentcore_task_id,
                status=status,
                result=result,
                error=error,
                metadata=deepcopy(self._agentcore_metadata),
            )
        except Exception as exc:
            logger.debug(f"Failed to sync agentcore task update: {exc}")

    def _extract_context(
        self, details: Optional[Dict] = None
    ) -> Dict[str, object]:
        context: Dict[str, object] = {}
        source = details or {}
        if not isinstance(source, dict):
            return context

        for key in _CONTEXT_KEYS:
            value = source.get(key)
            if value in (None, "", [], {}):
                continue
            context[key] = value

        task_type = source.get("task_type")
        if task_type not in (None, "", [], {}):
            context["task_type"] = task_type

        return context

    def _merge_context(self, details: Optional[Dict] = None) -> None:
        context = self._extract_context(details)
        if not context:
            return

        self._context.update(context)
        self._agentcore_metadata["context"] = deepcopy(self._context)

    def context_summary(self, details: Optional[Dict] = None) -> str:
        context = deepcopy(self._context)
        context.update(self._extract_context(details))

        parts = [self.task_type]
        for key in _CONTEXT_KEYS:
            value = context.get(key)
            if value in (None, "", [], {}):
                continue
            parts.append(f"{key}={value}")

        return (
            " | ".join([parts[0], " ".join(parts[1:])])
            if len(parts) > 1
            else parts[0]
        )

    def format_message(
        self,
        message: str,
        details: Optional[Dict] = None,
    ) -> str:
        context = self.context_summary(details)
        if not context:
            return message
        if not message:
            return f"[{context}]"
        return f"[{context}] {message}"

    def _build_log_entry(
        self,
        action: str,
        message: str,
        data: dict = None,
    ) -> Dict:
        self._merge_context(data)
        formatted_message = self.format_message(message, data)
        entry = {
            "timestamp": timezone.now().isoformat(),
            "step": action,
            "name": action,
            "action": action,
            "message": formatted_message,
            "raw_message": message,
            "level": "INFO",
            "context": deepcopy(self._context),
        }
        if data:
            entry.update(deepcopy(data))
        if "level" not in entry or not entry["level"]:
            entry["level"] = "INFO"
        return entry

    def set_task_id(self, task_id: str) -> None:
        if not task_id:
            return

        self._task_id = str(task_id)
        self._merge_context({"task_id": self._task_id})

        if self.task:
            try:
                self.task.task_id = self._task_id
                self.task.save(update_fields=["task_id"])
                logger.debug(
                    f"Set legacy task_id for {self.task_type} task: {task_id}"
                )
            except Exception as e:
                logger.error(f"Failed to set legacy task_id: {e}")

        if (
            self._agentcore_task_id
            and self._agentcore_task_id != self._task_id
        ):
            try:
                from agentcore_task.adapters.django.models import TaskExecution

                TaskExecution.objects.filter(
                    task_id=self._agentcore_task_id
                ).update(task_id=self._task_id)
                self._agentcore_task_id = self._task_id
            except Exception as e:
                logger.error(f"Failed to update agentcore task_id: {e}")

    def create_task(self, initial_details: Dict = None) -> EmailTask:
        if self.track_legacy:
            try:
                self.task = EmailTask.objects.create(
                    task_type=self.task_type,
                    status=EmailTask.TaskStatus.RUNNING,
                    started_at=timezone.now(),
                    details=deepcopy(initial_details or {}),
                )
                logger.debug(
                    f"Created legacy {self.task_type} task: {self.task.id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create legacy {self.task_type} task: {e}"
                )
                self.task = None

        self._merge_context(initial_details)

        self._task_id = self._task_id or _current_celery_task_id()
        if self._task_id:
            self._merge_context({"task_id": self._task_id})
        self._sync_agentcore_registration(initial_details or {})
        logger.info(f"{self.context_summary(initial_details)} started")
        return self.task

    def update_task(self, details: Dict) -> None:
        self._merge_context(details)
        if self.task:
            try:
                self.task.details = deepcopy(details)
                self.task.save(update_fields=["details"])
                logger.debug(
                    f"{self.context_summary(details)} updated legacy task "
                    f"{self.task.id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to update legacy {self.context_summary(details)} "
                    f"task: {e}"
                )

        self._sync_agentcore_update(
            "STARTED",
            metadata=_normalize_metadata(details),
        )

    def complete_task(self, details: Dict) -> None:
        self._merge_context(details)
        if self.task:
            try:
                self.task.status = EmailTask.TaskStatus.COMPLETED
                self.task.completed_at = timezone.now()
                self.task.details = deepcopy(details)
                self.task.save(
                    update_fields=["status", "completed_at", "details"]
                )
                logger.debug(
                    f"{self.context_summary(details)} completed legacy task "
                    f"{self.task.id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to complete legacy {self.context_summary(details)} "
                    f"task: {e}"
                )

        self._sync_agentcore_update(
            "SUCCESS",
            result=deepcopy(details),
            metadata=_normalize_metadata(details),
        )
        logger.info(f"{self.context_summary(details)} completed")

    def fail_task(self, details: Dict, error_msg: str) -> None:
        self._merge_context(details)
        if self.task:
            try:
                self.task.status = EmailTask.TaskStatus.FAILED
                self.task.completed_at = timezone.now()
                self.task.error_message = error_msg
                failure_details = deepcopy(details)
                if isinstance(failure_details, dict):
                    failure_details["error"] = error_msg
                    failure_details["failed_at"] = timezone.now().isoformat()
                self.task.details = failure_details
                self.task.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "error_message",
                        "details",
                    ]
                )
                logger.debug(
                    f"{self.context_summary(details)} marked legacy task "
                    f"failed: {self.task.id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to fail legacy {self.context_summary(details)} "
                    f"task: {e}"
                )

        failure_metadata = _normalize_metadata(details)
        failure_metadata["error"] = error_msg
        failure_metadata["failed_at"] = timezone.now().isoformat()
        self._sync_agentcore_update(
            "FAILURE",
            error=error_msg,
            metadata=failure_metadata,
        )

        self._queue_failure_notification(failure_metadata, error_msg)
        logger.error(f"{self.context_summary(details)} failed: {error_msg}")

    def _should_skip_failure_notification(self, details: Dict) -> bool:
        if self.task_type != "EMAIL_WORKFLOW":
            return False

        email_id = details.get("email_id")
        if not email_id:
            return False

        try:
            from threadline.models import EmailMessage

            return EmailMessage.objects.filter(
                id=email_id,
                status="failed",
            ).exists()
        except Exception as exc:
            logger.debug(
                f"Failed to inspect email status before notifying: {exc}"
            )
            return False

    def _queue_failure_notification(
        self, details: Dict, error_msg: str
    ) -> None:
        if self._should_skip_failure_notification(details):
            return

        try:
            from threadline.tasks.notifications import (
                send_threadline_failure_notification,
            )
        except Exception as exc:
            logger.debug(
                "Failed to import threadline failure notification task: "
                f"{exc}"
            )
            return

        user_id = details.get("user_id")

        try:
            send_threadline_failure_notification.delay(
                self.task_type,
                details,
                error_msg,
                user_id=user_id,
            )
        except Exception as exc:
            logger.debug(
                f"Failed to queue threadline failure notification: {exc}"
            )

    def append_task(
        self, action: str, message: str, data: dict = None
    ) -> None:
        log_entry = self._build_log_entry(action, message, data)

        if self.task:
            try:
                if isinstance(self.task.details, list):
                    details_list = self.task.details
                elif self.task.details:
                    details_list = [deepcopy(self.task.details)]
                else:
                    details_list = []

                details_list.append(log_entry)
                self.task.details = details_list
                self.task.save(update_fields=["details"])
                logger.debug(
                    f"Appended log to legacy {self.task_type} task: {action}"
                )
            except Exception as e:
                logger.error(f"Failed to append legacy task log: {e}")

        logger.debug(f"{self.context_summary(data)} step {action}: {message}")

        self._agentcore_metadata.setdefault("steps", [])
        self._agentcore_metadata["steps"].append(log_entry)
        self._agentcore_metadata.setdefault("task_logs", [])
        self._agentcore_metadata["task_logs"].append(log_entry)
        if "progress_percent" in log_entry:
            self._agentcore_metadata["progress_percent"] = log_entry[
                "progress_percent"
            ]
        if "progress_message" in log_entry:
            self._agentcore_metadata["progress_message"] = log_entry[
                "progress_message"
            ]
        self._agentcore_metadata["progress_step"] = action
        self._sync_agentcore_update(
            "STARTED",
            metadata={
                "steps": self._agentcore_metadata["steps"],
                "task_logs": self._agentcore_metadata["task_logs"],
                "progress_step": action,
            },
        )

    def update_task_status(self, new_status: str) -> None:
        if not self.task:
            return

        try:
            self.task.status = new_status
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
            logger.debug(
                f"Updated legacy {self.task_type} task status to: "
                f"{new_status}"
            )
        except Exception as e:
            logger.error(f"Failed to update legacy task status: {e}")

        agentcore_status = "STARTED"
        if new_status == EmailTask.TaskStatus.COMPLETED:
            agentcore_status = "SUCCESS"
        elif new_status in [
            EmailTask.TaskStatus.FAILED,
            EmailTask.TaskStatus.CANCELLED,
        ]:
            agentcore_status = "FAILURE"
        self._sync_agentcore_update(
            agentcore_status,
            metadata={"legacy_status": new_status},
        )
        logger.info(f"{self.context_summary()} status -> {new_status}")
