"""
Email merge coordination tasks.

This module provides an asynchronous merge coordination stage that runs
between email receipt and the main LangGraph workflow. It records merge
relationships without changing how each email processes its own content.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from agentcore_task.adapters.django import prevent_duplicate_task
from threadline.models import EmailMessage
from threadline.services.email_merge import EmailMergeService
from threadline.tasks.email_workflow import process_email_workflow
from threadline.utils.task_tracer import TaskTracer
from threadline.state_machine import (
    EMAIL_STATE_MACHINE,
    EmailStatus,
    can_transition_to,
)

logger = logging.getLogger(__name__)


def _mark_email_failed(
    email: EmailMessage | None,
    error_message: str,
) -> None:
    """
    Mark an email as failed when the state machine allows it.
    """
    if not email:
        return

    if can_transition_to(
        email.status,
        EmailStatus.FAILED.value,
        EMAIL_STATE_MACHINE,
    ):
        email.set_status(EmailStatus.FAILED.value, error_message=error_message)
        logger.warning(
            f"[Merge] Email {email.id} status set to FAILED after merge error"
        )
    else:
        logger.warning(
            f"[Merge] Skipped marking email {email.id} as FAILED because "
            f"status transition {email.status} -> {EmailStatus.FAILED.value} "
            "is not allowed"
        )


@shared_task
@prevent_duplicate_task(
    "process_email_merge",
    lock_param="email_id",
    timeout=settings.TASK_TIMEOUT_MINUTES * 60,
)
def process_email_merge(
    email_id: str,
    force: bool = False,
    language: str | None = None,
    scene: str | None = None,
    trigger_source: str | None = None,
) -> str:
    """
    Reconcile merge relationships for an email and enqueue workflow for the
    same record.
    """
    tracer = TaskTracer("EMAIL_MERGE")
    task_id = getattr(process_email_merge.request, "id", "") or ""
    tracer.set_task_id(task_id)
    merge_failure_logged = False

    try:
        email = EmailMessage.objects.select_related("user", "merged_into").get(
            id=email_id
        )
        has_merged_children = email.merged_children.exists()
        merge_result = {
            "email_id": str(email.id),
            "anchor_email_id": str(email.id),
            "should_merge": False,
            "merge_reason": "manual_merge_skip" if has_merged_children else "",
            "source_count": 0,
        }
        user_info = f"{email.user.username}({email.user_id})"
        merge_context = tracer.context_summary(
            {
                "email_id": str(email_id),
                "user_id": str(email.user_id),
                "force": force,
                "language": language,
                "scene": scene,
                "trigger_source": trigger_source,
            }
        )
        logger.info(
            f"{merge_context} [Merge] Starting for email {email_id}, "
            f"user {user_info}, trigger_source={trigger_source or 'unknown'}"
        )
        logger.debug(
            (
                "[Merge] email snapshot "
                "email_id=%s uuid=%s subject=%r received_at=%s status=%s "
                "merged_into_id=%s raw_message_id=%s in_reply_to=%s "
                "references=%s"
            ),
            email.id,
            email.uuid,
            email.subject,
            email.received_at,
            email.status,
            email.merged_into_id,
            email.raw_message_id,
            email.in_reply_to,
            email.references,
        )

        tracer.create_task(
            {
                "email_id": str(email.id),
                "user_id": str(email.user_id),
                "force": force,
                "language": language,
                "scene": scene,
                "trigger_source": trigger_source,
                "status": "starting",
            }
        )
        if has_merged_children:
            merge_result["merge_reason"] = "manual_merge_skip"
            logger.info(
                (
                    "[Merge] Skipping automatic reconciliation for email "
                    "with merged children email_id=%s uuid=%s"
                ),
                email.id,
                email.uuid,
            )
            tracer.append_task(
                "MERGE_RECONCILE",
                "Merge reconciliation skipped for canonical email",
                {
                    "email_id": str(email.id),
                    "anchor_email_id": str(email.id),
                    "should_merge": False,
                    "merge_reason": merge_result["merge_reason"],
                    "source_count": 0,
                },
            )
        else:
            merge_service = EmailMergeService()
            candidates = list(merge_service._candidate_queryset(email))
            logger.info(
                "[Merge] candidate scan email_id=%s candidate_count=%s",
                email.id,
                len(candidates),
            )
            for candidate in candidates:
                matched, reason = merge_service._match_candidate(email, candidate)
                logger.debug(
                    (
                        "[Merge] candidate detail "
                        "email_id=%s candidate_id=%s candidate_uuid=%s "
                        "subject=%r received_at=%s text_len=%s matched=%s "
                        "reason=%s"
                    ),
                    email.id,
                    candidate.id,
                    candidate.uuid,
                    candidate.subject,
                    candidate.received_at,
                    len(candidate.text_content or ""),
                    matched,
                    reason,
                )
            related_email, decision = merge_service.reconcile(email)
            logger.info(
                (
                    "[Merge] reconcile result "
                    "email_id=%s anchor_id=%s anchor_uuid=%s "
                    "should_merge=%s reason=%s source_ids=%s"
                ),
                email.id,
                related_email.id,
                related_email.uuid,
                decision.should_merge,
                decision.reason,
                [source.id for source in decision.sources],
            )

            tracer.append_task(
                "MERGE_RECONCILE",
                "Merge reconciliation completed",
                {
                    "email_id": str(email.id),
                    "anchor_email_id": str(related_email.id),
                    "should_merge": decision.should_merge,
                    "merge_reason": decision.reason,
                    "source_count": len(decision.sources),
                },
            )
            merge_result = {
                **merge_result,
                "anchor_email_id": str(related_email.id),
                "should_merge": decision.should_merge,
                "merge_reason": decision.reason,
                "source_count": len(decision.sources),
            }

        try:
            process_email_workflow.delay(
                str(email.id),
                force=force,
                language=language,
                scene=scene,
                trigger_source=trigger_source,
            )
        except Exception as exc:
            merge_failure_logged = True
            logger.error(
                f"[Merge] Failed to enqueue workflow for email " f"{email.id}: {exc}"
            )
            _mark_email_failed(email, str(exc))
            tracer.fail_task(
                {**merge_result, "status": "failed"},
                str(exc),
            )
            raise
        tracer.complete_task({**merge_result, "status": "completed"})
        return str(email.id)

    except EmailMessage.DoesNotExist:
        logger.error(f"[Merge] EmailMessage {email_id} not found")
        tracer.fail_task(
            {"email_id": str(email_id), "status": "failed"},
            f"Email with id {email_id} not found",
        )
        raise ValueError(f"Email with id {email_id} not found")
    except Exception as exc:
        logger.error(f"[Merge] Failed to execute for email {email_id}: {exc}")
        if not merge_failure_logged:
            try:
                email_obj = locals().get("email")
                _mark_email_failed(email_obj, str(exc))
            except Exception as status_exc:
                logger.error(
                    f"[Merge] Failed to mark email {email_id} as FAILED: "
                    f"{status_exc}"
                )
            tracer.fail_task(
                {"email_id": str(email_id), "status": "failed"},
                str(exc),
            )
        raise
