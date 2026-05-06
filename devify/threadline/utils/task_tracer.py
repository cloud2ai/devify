"""
Task Tracer Utility

Records task execution state in agentcore-task's TaskExecution records.
Legacy EmailTask tracking has been removed; task visibility now comes
from agentcore only.
"""

from __future__ import annotations

import math
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from uuid import uuid4
from typing import Dict, Optional

from celery import current_task
from django.utils import timezone

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


def _stage_percent(
    plan: Dict[str, dict] | None,
    stage: str,
    *,
    ratio: float | None = None,
    step_index: int | None = None,
    step_total: int | None = None,
) -> int:
    stage_plan = (plan or {}).get(stage) or {}
    start = int(stage_plan.get("start", 0) or 0)
    span = int(stage_plan.get("span", 0) or 0)

    if span <= 0:
        return max(0, min(100, start))

    if step_index is not None and step_total:
        try:
            step_index = max(0, int(step_index))
            step_total = max(1, int(step_total))
            ratio = step_index / step_total
        except (TypeError, ValueError, ZeroDivisionError):
            ratio = None

    if ratio is None:
        ratio = 1.0

    try:
        normalized_ratio = max(0.0, min(1.0, float(ratio)))
    except (TypeError, ValueError):
        normalized_ratio = 1.0

    return max(0, min(100, int(round(start + (span * normalized_ratio)))))


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
    Task tracer for agentcore TaskExecution records.
    """

    def __init__(
        self,
        task_type: str,
        module: str = "threadline",
    ):
        self.task_type = task_type
        self.module = module
        self._task_id: Optional[str] = None
        self._agentcore_task_id: Optional[str] = None
        self._agentcore_metadata: Dict = {}
        self._context: Dict[str, object] = {}
        self._progress_total_steps: Optional[int] = None
        self._progress_current_step: int = 0
        self._threadline_progress_percent: Optional[int] = None

    @property
    def task_id(self) -> Optional[str]:
        return self._agentcore_task_id or self._task_id

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

    def _sync_threadline_progress_snapshot(
        self,
        details: Optional[Dict] = None,
    ) -> None:
        """
        Mirror workflow progress onto the user-facing EmailMessage row.

        Only the email workflow should surface progress to normal users.
        The snapshot stays intentionally small: a single percentage and
        timestamp, so the detail page can render a stable progress bar.
        """
        if self.task_type not in {"EMAIL_MERGE", "EMAIL_WORKFLOW"}:
            return

        email_id = self._context.get("email_id")
        if not email_id:
            return

        payload = _normalize_metadata(details)
        percent = payload.get("progress_percent")

        if percent is None:
            percent = self._agentcore_metadata.get("progress_percent")

        if percent is None and self._progress_total_steps:
            try:
                percent = int(
                    math.floor(
                        (
                            max(self._progress_current_step, 0)
                            / self._progress_total_steps
                        )
                        * 100
                    )
                )
            except Exception:
                percent = None

        if percent is None:
            return

        try:
            normalized = max(0, min(100, int(percent)))
        except (TypeError, ValueError):
            return

        if self._threadline_progress_percent is not None:
            normalized = max(self._threadline_progress_percent, normalized)
        self._threadline_progress_percent = normalized

        # Scale task-local progress into an end-to-end progress bar.
        if self.task_type == "EMAIL_MERGE":
            normalized = max(0, min(20, int(round(normalized * 0.2))))
        else:
            if normalized == 0 and payload.get("status") == "starting":
                normalized = 0
            else:
                normalized = max(
                    20,
                    min(100, int(round(20 + normalized * 0.8))),
                )

        try:
            from threadline.models import EmailMessage

            message = (
                EmailMessage.objects.filter(id=email_id)
                .only("id", "metadata")
                .first()
            )
            if not message:
                return

            message.set_processing_progress(normalized)
            logger.info(
                "%s synced threadline progress percent=%s step=%s",
                self.context_summary(
                    {
                        "email_id": email_id,
                        "progress_percent": normalized,
                        "progress_step": payload.get("progress_step"),
                    }
                ),
                normalized,
                payload.get("progress_step"),
            )
        except Exception as exc:
            logger.debug(
                "Failed to sync threadline progress snapshot for %s: %s",
                email_id,
                exc,
            )

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

    def set_progress_total_steps(self, total_steps: Optional[int]) -> None:
        try:
            normalized = int(total_steps) if total_steps is not None else None
        except (TypeError, ValueError):
            return

        if normalized is None or normalized <= 0:
            return

        self._progress_total_steps = normalized
        self._agentcore_metadata["progress_total_steps"] = normalized
        if self._progress_current_step > normalized:
            self._progress_current_step = normalized

    def _build_progress_fields(
        self,
        action: str,
        message: str,
        data: Optional[Dict] = None,
        *,
        advance: bool = False,
    ) -> Dict[str, object]:
        payload = _normalize_metadata(data)
        progress_plan = payload.pop("progress_plan", None)
        if progress_plan is None:
            progress_plan = self._agentcore_metadata.get("progress_plan")

        has_explicit_progress_fields = any(
            key in payload
            for key in (
                "progress_percent",
                "progress_ratio",
                "progress_stage",
                "progress_current_step",
                "progress_total_steps",
            )
        )

        if not advance and not has_explicit_progress_fields:
            return {}

        total_steps = payload.get("progress_total_steps")
        current_step = payload.get("progress_current_step")

        if total_steps is not None:
            self.set_progress_total_steps(total_steps)
        if self._progress_total_steps is not None:
            payload["progress_total_steps"] = self._progress_total_steps

        stage_name = payload.get("progress_stage")
        ratio = payload.get("progress_ratio")
        current_step = payload.get("progress_current_step")
        total_steps = payload.get("progress_total_steps")

        if "progress_percent" not in payload and stage_name and progress_plan:
            try:
                payload["progress_percent"] = _stage_percent(
                    progress_plan,
                    stage_name,
                    ratio=ratio,
                    step_index=current_step,
                    step_total=total_steps,
                )
            except Exception:
                payload.pop("progress_percent", None)

        if advance:
            self._progress_current_step += 1
            if self._progress_total_steps is not None:
                self._progress_current_step = min(
                    self._progress_current_step,
                    self._progress_total_steps,
                )
            current_step = self._progress_current_step
        elif current_step is not None:
            try:
                current_step = int(current_step)
            except (TypeError, ValueError):
                current_step = None

        if current_step is not None:
            self._progress_current_step = max(
                self._progress_current_step,
                int(current_step),
            )
            payload["progress_current_step"] = int(current_step)

        if self._progress_total_steps is not None and current_step is not None:
            normalized_current = min(
                max(int(current_step), 0),
                self._progress_total_steps,
            )
            payload["progress_current_step"] = normalized_current
            payload["progress_percent"] = 100 if (
                normalized_current >= self._progress_total_steps
            ) else int(
                math.floor(
                    (normalized_current / self._progress_total_steps) * 100
                )
            )
        elif "progress_percent" in payload:
            try:
                payload["progress_percent"] = max(
                    0,
                    min(100, int(payload["progress_percent"])),
                )
            except (TypeError, ValueError):
                payload.pop("progress_percent", None)
        else:
            payload.pop("progress_percent", None)

        if "progress_message" not in payload and message:
            payload["progress_message"] = message
        payload["progress_step"] = action
        return payload

    def advance_progress(
        self,
        action: str,
        message: str,
        data: Optional[Dict] = None,
    ) -> None:
        progress_payload = self._build_progress_fields(
            action,
            message,
            data,
            advance=True,
        )
        self.append_task(action, message, progress_payload)

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
        entry.pop("progress_plan", None)
        if "level" not in entry or not entry["level"]:
            entry["level"] = "INFO"
        return entry

    def set_task_id(self, task_id: str) -> None:
        if not task_id:
            return

        self._task_id = str(task_id)
        self._merge_context({"task_id": self._task_id})

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

    def create_task(self, initial_details: Dict = None) -> str:
        self._threadline_progress_percent = None
        self._merge_context(initial_details)
        if initial_details:
            self.set_progress_total_steps(
                initial_details.get("progress_total_steps")
            )

        self._task_id = self._task_id or _current_celery_task_id()
        if self._task_id:
            self._merge_context({"task_id": self._task_id})
        self._sync_threadline_progress_snapshot(initial_details)
        self._sync_agentcore_registration(initial_details or {})
        logger.info(f"{self.context_summary(initial_details)} started")
        return self._agentcore_task_id or self._task_id

    def update_task(self, details: Dict) -> None:
        self._merge_context(details)
        if details:
            self.set_progress_total_steps(details.get("progress_total_steps"))

        self._sync_agentcore_update(
            "STARTED",
            metadata=_normalize_metadata(details),
        )

    def complete_task(self, details: Dict) -> None:
        self._merge_context(details)

        completion_details = _normalize_metadata(details)
        if "progress_percent" not in completion_details:
            completion_details["progress_percent"] = 100
        if self._progress_total_steps is not None:
            completion_details.setdefault(
                "progress_total_steps",
                self._progress_total_steps,
            )
        if self._progress_total_steps is not None:
            completion_details.setdefault(
                "progress_current_step",
                self._progress_total_steps,
            )
        completion_details.setdefault("progress_step", "COMPLETE")
        if completion_details.get("progress_message") is None and details:
            completion_details["progress_message"] = details.get(
                "progress_message"
            ) or "Completed"

        self._agentcore_metadata.update(completion_details)

        self._sync_agentcore_update(
            "SUCCESS",
            result=deepcopy(details),
            metadata=completion_details,
        )
        self._sync_threadline_progress_snapshot(completion_details)
        logger.info(f"{self.context_summary(details)} completed")

    def fail_task(self, details: Dict, error_msg: str) -> None:
        self._merge_context(details)

        failure_metadata = _normalize_metadata(details)
        failure_metadata["error"] = error_msg
        failure_metadata["failed_at"] = timezone.now().isoformat()
        self._agentcore_metadata.update(failure_metadata)
        self._sync_agentcore_update(
            "FAILURE",
            error=error_msg,
            metadata=failure_metadata,
        )
        self._sync_threadline_progress_snapshot(failure_metadata)

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
        progress_fields = self._build_progress_fields(action, message, data)
        log_entry.update(progress_fields)

        context = self.context_summary(data)
        if progress_fields:
            logger.info(
                "%s progress step=%s percent=%s current_step=%s total_steps=%s message=%s",
                context,
                log_entry.get("progress_step", action),
                log_entry.get("progress_percent"),
                log_entry.get("progress_current_step"),
                log_entry.get("progress_total_steps"),
                message,
            )
        else:
            logger.debug(f"{context} step {action}: {message}")

        self._agentcore_metadata.setdefault("steps", [])
        self._agentcore_metadata["steps"].append(log_entry)
        self._agentcore_metadata.setdefault("task_logs", [])
        self._agentcore_metadata["task_logs"].append(log_entry)
        for key in (
            "progress_percent",
            "progress_message",
            "progress_step",
            "progress_total_steps",
            "progress_current_step",
        ):
            if key in log_entry:
                self._agentcore_metadata[key] = log_entry[key]
        progress_metadata = {
            key: log_entry[key]
            for key in (
                "progress_percent",
                "progress_message",
                "progress_step",
                "progress_total_steps",
                "progress_current_step",
            )
            if key in log_entry
        }
        self._sync_agentcore_update(
            "STARTED",
            metadata={
                "steps": self._agentcore_metadata["steps"],
                "task_logs": self._agentcore_metadata["task_logs"],
                **progress_metadata,
            },
        )
        self._sync_threadline_progress_snapshot(progress_metadata)

    def update_task_status(self, new_status: str) -> None:
        agentcore_status = "STARTED"
        if new_status in ("COMPLETED", "SUCCESS"):
            agentcore_status = "SUCCESS"
        elif new_status in ("FAILED", "CANCELLED", "FAILURE"):
            agentcore_status = "FAILURE"
        self._sync_agentcore_update(
            agentcore_status,
            metadata={"legacy_status": new_status},
        )
        logger.info(f"{self.context_summary()} status -> {new_status}")
