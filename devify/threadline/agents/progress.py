"""
Workflow progress helpers.

These helpers turn the email workflow into a percentage plan that can be
updated from individual workflow stages and substeps.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Dict, Mapping


WORKFLOW_STAGES = (
    "prepare",
    "credits",
    "images",
    "llm",
    "summary",
    "metadata",
    "finalize",
)


def _bounded_int(value: int | float | None, minimum: int = 0) -> int:
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return minimum


def _has_value(value) -> bool:
    return value not in (None, "", [], {})


def _attachment_is_pending(attachment) -> bool:
    if isinstance(attachment, Mapping):
        return not _has_value(attachment.get("llm_content"))

    return not _has_value(getattr(attachment, "llm_content", None))


def _normalize_stage_units(
    stage_units: Mapping[str, int] | None = None,
) -> OrderedDict[str, int]:
    units: OrderedDict[str, int] = OrderedDict(
        (stage, 0) for stage in WORKFLOW_STAGES
    )
    if stage_units:
        for stage in WORKFLOW_STAGES:
            units[stage] = _bounded_int(stage_units.get(stage, 0))

    if sum(units.values()) <= 0:
        units["finalize"] = 1

    return units


def estimate_initial_workflow_units(
    *,
    email,
    force: bool = False,
) -> OrderedDict[str, int]:
    """
    Estimate workflow units before the prepare node runs.

    This is intentionally coarse. The prepare node refines the estimate
    once it has loaded the full workflow state.
    """
    attachments = list(email.attachments.filter(is_image=True))
    text_content = (email.text_content or "").strip()

    return OrderedDict(
        [
            ("prepare", 1),
            ("credits", 1),
            (
                "images",
                sum(
                    1
                    for att in attachments
                    if force or _attachment_is_pending(att)
                ),
            ),
            (
                "llm",
                (
                    10
                    if text_content
                    and (force or not _has_value(email.llm_content))
                    else 0
                ),
            ),
            (
                "summary",
                int(force or not _has_value(email.summary_title))
                + int(force or not _has_value(email.summary_data)),
            ),
            (
                "metadata",
                1 if force or not _has_value(email.metadata) else 0,
            ),
            ("finalize", 1),
        ]
    )


def estimate_prepare_workflow_units(
    *,
    state: Mapping[str, object],
) -> OrderedDict[str, int]:
    """
    Estimate workflow units from the fully prepared workflow state.
    """
    force = bool(state.get("force"))
    attachments = list(state.get("attachments") or [])
    max_attachments = state.get("max_attachments")
    try:
        max_attachments = (
            int(max_attachments) if max_attachments is not None else None
        )
    except (TypeError, ValueError):
        max_attachments = None

    image_attachments = [
        att
        for att in attachments
        if isinstance(att, Mapping) and att.get("is_image")
    ]
    image_attachments.sort(
        key=lambda att: _bounded_int(att.get("file_size")),
        reverse=True,
    )
    if max_attachments is not None and max_attachments >= 0:
        image_attachments = image_attachments[:max_attachments]

    text_content = (state.get("text_content") or "").strip()
    summary_title = state.get("summary_title")
    summary_data = state.get("summary_data")
    metadata = state.get("metadata")

    return OrderedDict(
        [
            ("prepare", 1),
            ("credits", 1),
            (
                "images",
                sum(
                    1
                    for attachment in image_attachments
                    if force or _attachment_is_pending(attachment)
                ),
            ),
            (
                "llm",
                (
                    10
                    if text_content
                    and (force or not _has_value(state.get("llm_content")))
                    else 0
                ),
            ),
            (
                "summary",
                int(force or not _has_value(summary_title))
                + int(force or not _has_value(summary_data)),
            ),
            (
                "metadata",
                1 if force or not _has_value(metadata) else 0,
            ),
            ("finalize", 1),
        ]
    )


def build_workflow_progress_plan(
    stage_units: Mapping[str, int] | None = None,
) -> Dict[str, dict]:
    """
    Build a monotonic 0-100 progress plan from workflow unit counts.
    """
    units = _normalize_stage_units(stage_units)
    total_units = sum(units.values()) or 1

    raw_spans = [
        (units[stage] / total_units) * 100 for stage in WORKFLOW_STAGES
    ]
    floored = [int(math.floor(span)) for span in raw_spans]
    remainder = 100 - sum(floored)
    fractions = [
        (span - math.floor(span), index)
        for index, span in enumerate(raw_spans)
    ]
    fractions.sort(reverse=True)

    for _, index in fractions[:remainder]:
        floored[index] += 1

    plan: Dict[str, dict] = {}
    cursor = 0
    for stage, span in zip(WORKFLOW_STAGES, floored):
        start = cursor
        end = cursor + span
        plan[stage] = {
            "start": start,
            "end": end,
            "span": span,
            "units": units[stage],
        }
        cursor = end

    if plan:
        last_stage = WORKFLOW_STAGES[-1]
        plan[last_stage]["end"] = 100
        plan[last_stage]["span"] = 100 - plan[last_stage]["start"]

    return plan


def _stage_span(plan: Dict[str, dict] | None, stage: str) -> int:
    if not plan:
        return 0
    stage_plan = plan.get(stage) or {}
    try:
        return int(stage_plan.get("span", 0))
    except (TypeError, ValueError):
        return 0


def stage_percent(
    plan: Dict[str, dict] | None,
    stage: str,
    *,
    ratio: float | None = None,
    step_index: int | None = None,
    step_total: int | None = None,
) -> int:
    """
    Convert a stage-local ratio or step index into an absolute percent.
    """
    stage_plan = (plan or {}).get(stage) or {}
    start = int(stage_plan.get("start", 0) or 0)
    span = _stage_span(plan, stage)

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
