"""
Email merge helpers for conservative thread consolidation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional

from django.db import transaction
from django.utils import timezone
from rapidfuzz import fuzz

from threadline.models import EmailMessage

logger = logging.getLogger(__name__)


THREAD_HEADER_PATTERN = re.compile(r"<([^>]+)>")
SUBJECT_PREFIX_PATTERN = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.I)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class MergeDecision:
    target: Optional[EmailMessage]
    reason: str = ""
    sources: tuple[EmailMessage, ...] = ()

    @property
    def should_merge(self) -> bool:
        return self.target is not None


class EmailMergeService:
    """
    Conservative relation helper for EmailMessage records.

    The current strategy only records merge relationships between messages
    that clearly belong to the same conversation. Each email still keeps its
    own processing results; merge does not rewrite content.
    """

    # Keep the merge window narrow for content-based matches, but allow
    # thread-header matches to look farther back because replies are often
    # delayed while still being causally related.
    CONTENT_WINDOW_DAYS = 3
    THREAD_RELATION_WINDOW_DAYS = 30
    # Lower the similarity bar slightly so near-duplicate forwards / reply
    # copies can merge without needing exact containment.
    RAPIDFUZZ_RATIO_THRESHOLD = 65.0
    RAPIDFUZZ_PARTIAL_RATIO_THRESHOLD = 80.0
    MIN_TEXT_EXTENSION = 40
    MIN_TEXT_EXTENSION_RATIO = 0.30

    def decide(self, email: EmailMessage) -> MergeDecision:
        """
        Find a related target for the given email if mergeable.
        """
        logger.info(
            "[EmailMerge] decide start email_id=%s uuid=%s subject=%r received_at=%s status=%s merged_into_id=%s",
            email.id,
            email.uuid,
            email.subject,
            email.received_at,
            email.status,
            email.merged_into_id,
        )
        if email.merged_into_id:
            # Once a record already has a relation, keep following that
            # relation instead of re-deciding against the candidate set.
            canonical = self.resolve_canonical(email)
            logger.info(
                "[EmailMerge] decide short-circuit email_id=%s target_id=%s target_uuid=%s reason=%s",
                email.id,
                canonical.id,
                canonical.uuid,
                email.merge_reason,
            )
            return MergeDecision(target=canonical, reason=email.merge_reason)

        # Find older canonical candidates that appear to belong to the same
        # conversation cluster as the current email.
        matched_sources = self._find_merge_sources(email)
        logger.info(
            "[EmailMerge] decide matched_sources email_id=%s matched_source_ids=%s",
            email.id,
            [source.id for source in matched_sources],
        )
        if matched_sources:
            # Pick the earliest matching record as a stable relation anchor.
            target = self._select_merge_target(matched_sources)
            logger.info(
                "[EmailMerge] decide target email_id=%s target_id=%s target_uuid=%s reason=%s",
                email.id,
                target.id,
                target.uuid,
                self._determine_merge_reason(email, matched_sources),
            )
            return MergeDecision(
                target=target,
                reason=self._determine_merge_reason(email, matched_sources),
                sources=tuple(matched_sources),
            )

        return MergeDecision(target=None)

    def reconcile(self, email: EmailMessage) -> tuple[EmailMessage, MergeDecision]:
        """
        Apply the merge decision and return the related record.
        """
        with transaction.atomic():
            email = EmailMessage.objects.select_for_update().get(pk=email.pk)

            if email.merged_into_id:
                # A retry on an already-merged record should continue from the
                # canonical record, not create a new branch.
                canonical = self.resolve_canonical(email)
                return (
                    canonical,
                    MergeDecision(
                        target=canonical,
                        reason=email.merge_reason,
                    ),
                )

            decision = self.decide(email)
            logger.info(
                "[EmailMerge] reconcile decision email_id=%s should_merge=%s target_id=%s target_uuid=%s source_ids=%s reason=%s",
                email.id,
                decision.should_merge,
                getattr(decision.target, "id", None),
                getattr(decision.target, "uuid", None),
                [source.id for source in decision.sources],
                decision.reason,
            )

            if decision.should_merge and decision.target:
                target = EmailMessage.objects.select_for_update().get(
                    pk=decision.target.pk
                )
                self._mark_source_as_merged(
                    email,
                    target,
                    decision.reason,
                    timezone.now(),
                )
                return target, decision

            self._mark_canonical(email)
            return email, decision

    def resolve_canonical(self, email: EmailMessage) -> EmailMessage:
        """
        Follow merge links until reaching the canonical record.
        """
        current = email
        visited: set[int] = set()

        while current.merged_into_id:
            # Guard against malformed merge chains so retries do not loop
            # forever if the data ever becomes cyclic.
            if current.pk in visited:
                logger.warning(
                    "Detected circular merge chain for email %s", current.pk
                )
                break
            visited.add(current.pk)
            current = current.merged_into

        return current

    def _find_merge_sources(self, email: EmailMessage) -> list[EmailMessage]:
        """
        Return all nearby messages that may be related to this email.
        """
        matched_sources: list[EmailMessage] = []
        for candidate in self._candidate_queryset(email):
            # Candidate scanning stays conservative: we log every record in the
            # time window, but only merge when a matcher explicitly fires.
            logger.debug(
                "[EmailMerge] candidate scan email_id=%s candidate_id=%s candidate_uuid=%s subject=%r received_at=%s status=%s",
                email.id,
                candidate.id,
                candidate.uuid,
                candidate.subject,
                candidate.received_at,
                candidate.status,
            )
            if self._candidate_matches(email, candidate):
                matched_sources.append(candidate)
                logger.debug(
                    "[EmailMerge] candidate matched email_id=%s candidate_id=%s",
                    email.id,
                    candidate.id,
                )
            else:
                logger.debug(
                    "[EmailMerge] candidate not matched email_id=%s candidate_id=%s",
                    email.id,
                    candidate.id,
                )
        return matched_sources

    def _select_merge_target(
        self, sources: Iterable[EmailMessage]
    ) -> EmailMessage:
        """
        Choose a deterministic relation anchor within the related cluster.
        """
        candidates = list(sources)
        logger.info(
            "[EmailMerge] select target cluster candidate_ids=%s received_at=%s",
            [item.id for item in candidates],
            [
                {
                    "id": item.id,
                    "uuid": str(item.uuid),
                    "received_at": item.received_at.isoformat()
                    if item.received_at
                    else None,
                }
                for item in candidates
            ],
        )
        return self._pick_earliest_candidate(candidates)

    def _candidate_matches(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        """
        Return True when a candidate should be merged into the current email.
        """
        # Matchers are ordered from strongest to weakest signal.
        if self._matches_thread_relation(email, candidate):
            logger.debug(
                "[EmailMerge] matcher hit thread_relation email_id=%s candidate_id=%s",
                email.id,
                candidate.id,
            )
            return True
        if self._matches_forward_chain(email, candidate):
            logger.debug(
                "[EmailMerge] matcher hit forward_chain email_id=%s candidate_id=%s",
                email.id,
                candidate.id,
            )
            return True
        if self._matches_text_similarity(email, candidate):
            logger.debug(
                "[EmailMerge] matcher hit text_similarity email_id=%s candidate_id=%s",
                email.id,
                candidate.id,
            )
            return True
        if self._matches_containment(email, candidate):
            logger.debug(
                "[EmailMerge] matcher hit containment email_id=%s candidate_id=%s",
                email.id,
                candidate.id,
            )
            return True
        logger.debug(
            "[EmailMerge] matcher miss email_id=%s candidate_id=%s",
            email.id,
            candidate.id,
        )
        return False

    def _match_candidate(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> tuple[bool, str | None]:
        """
        Backward-compatible matcher that returns the boolean result and reason.

        The merge task still logs the reason per candidate, so keep this helper
        as the stable contract and derive it from the newer matcher methods.
        """
        reason = self._candidate_match_reason(email, candidate)
        return bool(reason), reason

    def _determine_merge_reason(
        self, email: EmailMessage, sources: Iterable[EmailMessage]
    ) -> str:
        """
        Pick the strongest reason among matched sources.
        """
        # Preserve the strongest explanation so the merge provenance remains
        # useful when several weak signals point to the same cluster.
        for source in sources:
            if (
                self._candidate_match_reason(email, source)
                == EmailMessage.MergeReason.THREAD_RELATION.value
            ):
                return EmailMessage.MergeReason.THREAD_RELATION.value
        for source in sources:
            if (
                self._candidate_match_reason(email, source)
                == EmailMessage.MergeReason.FORWARD_CHAIN.value
            ):
                return EmailMessage.MergeReason.FORWARD_CHAIN.value
        return EmailMessage.MergeReason.TEXT_SIMILARITY.value

    def _candidate_match_reason(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> str | None:
        """
        Return the strongest merge reason for a candidate.
        """
        if self._matches_thread_relation(email, candidate):
            return EmailMessage.MergeReason.THREAD_RELATION.value
        if self._matches_forward_chain(email, candidate):
            return EmailMessage.MergeReason.FORWARD_CHAIN.value
        if self._matches_text_similarity(email, candidate):
            return EmailMessage.MergeReason.TEXT_SIMILARITY.value
        if self._matches_containment(email, candidate):
            return EmailMessage.MergeReason.TEXT_SIMILARITY.value
        return None

    def _matches_thread_relation(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        if not self._within_time_window(
            email, candidate, self.THREAD_RELATION_WINDOW_DAYS
        ):
            return False

        candidate_ids = []
        if email.in_reply_to:
            candidate_ids.extend(self._extract_message_tokens(email.in_reply_to))
        candidate_ids.extend(
            self._extract_reference_tokens(email.references)
        )

        if not candidate_ids:
            return False

        return bool(
            candidate.raw_message_id in candidate_ids
            or candidate.message_id in candidate_ids
        )

    def _matches_forward_chain(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        if not self._within_time_window(
            email, candidate, self.CONTENT_WINDOW_DAYS
        ):
            return False

        normalized_subject = self._normalize_subject(email.subject)
        if not normalized_subject:
            return False

        if not self._subject_looks_forward(email.subject):
            return False

        candidate_subject = self._normalize_subject(candidate.subject)
        if candidate_subject != normalized_subject:
            return False

        return self._matches_text_similarity(email, candidate)

    def _matches_text_similarity(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        if not self._within_time_window(
            email, candidate, self.CONTENT_WINDOW_DAYS
        ):
            return False

        normalized_subject = self._normalize_subject(email.subject)
        if not normalized_subject:
            return False

        if self._normalize_subject(candidate.subject) != normalized_subject:
            return False

        # Keep the merge heuristic simple and predictable: only compare raw
        # extracted text. If a record has no text_content, skip it instead of
        # trying to infer from HTML.
        current_text = self._normalize_text(email.text_content)
        candidate_text = self._normalize_text(candidate.text_content)
        if not current_text or not candidate_text:
            return False

        ratio, partial_ratio = self._text_similarity_scores(
            candidate_text, current_text
        )
        logger.debug(
            "[EmailMerge] rapidfuzz similarity email_id=%s candidate_id=%s ratio=%.2f partial_ratio=%.2f",
            email.id,
            candidate.id,
            ratio,
            partial_ratio,
        )
        return self._meets_text_similarity_threshold(ratio, partial_ratio)

    def _matches_containment(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        if not self._within_time_window(
            email, candidate, self.CONTENT_WINDOW_DAYS
        ):
            return False

        current_text = self._normalize_text(email.text_content)
        candidate_text = self._normalize_text(candidate.text_content)
        if not current_text or not candidate_text:
            return False
        return self._is_strong_containment(candidate_text, current_text)

    def _candidate_queryset(self, email: EmailMessage):
        """
        Base queryset for same-user relation candidates.
        """
        # Only search within the same user and a symmetric time window; this
        # keeps the relation pass fast and avoids cross-user contamination.
        window_start = email.received_at - timedelta(
            days=self.THREAD_RELATION_WINDOW_DAYS
        )
        window_end = email.received_at + timedelta(
            days=self.THREAD_RELATION_WINDOW_DAYS
        )
        return (
            EmailMessage.objects.filter(
                user_id=email.user_id,
                received_at__gte=window_start,
                received_at__lte=window_end,
            )
            .exclude(pk=email.pk)
            .order_by("received_at", "id")
        )

    def _pick_earliest_candidate(
        self, candidates: Iterable[EmailMessage]
    ) -> Optional[EmailMessage]:
        """
        Pick the earliest relation candidate from a candidate list.
        """
        materialized = list(candidates)
        if not materialized:
            return None
        return sorted(materialized, key=lambda item: (item.received_at, item.id))[0]

    def _pick_text_candidate(
        self, email: EmailMessage, candidates: Iterable[EmailMessage]
    ) -> Optional[EmailMessage]:
        """
        Pick a candidate that strongly matches the new text.
        """
        current_text = self._normalize_text(email.text_content)
        if not current_text:
            return None

        best_candidate = None
        best_score = 0.0
        best_ratio = 0.0
        best_partial_ratio = 0.0

        for candidate in candidates:
            candidate_text = self._normalize_text(candidate.text_content)
            if not candidate_text:
                continue

            if not self._is_continuation(candidate_text, current_text):
                continue

            ratio, partial_ratio = self._text_similarity_scores(
                candidate_text, current_text
            )
            score = max(ratio, partial_ratio)
            if score > best_score:
                best_candidate = candidate
                best_score = score
                best_ratio = ratio
                best_partial_ratio = partial_ratio

        if best_candidate and self._meets_text_similarity_threshold(
            best_ratio, best_partial_ratio
        ):
            return best_candidate
        return None

    def _text_similarity_scores(
        self, candidate_text: str, current_text: str
    ) -> tuple[float, float]:
        """
        Return lexical similarity scores from RapidFuzz.
        """
        ratio = float(fuzz.ratio(candidate_text, current_text))
        partial_ratio = float(fuzz.partial_ratio(candidate_text, current_text))
        return ratio, partial_ratio

    def _meets_text_similarity_threshold(
        self, ratio: float, partial_ratio: float
    ) -> bool:
        """
        Return True when either RapidFuzz score reaches the merge threshold.
        """
        return (
            ratio >= self.RAPIDFUZZ_RATIO_THRESHOLD
            or partial_ratio >= self.RAPIDFUZZ_PARTIAL_RATIO_THRESHOLD
        )

    def _within_time_window(
        self,
        email: EmailMessage,
        candidate: EmailMessage,
        days: int,
    ) -> bool:
        """
        Return True when two records fall within a symmetric time window.
        """
        delta = abs(email.received_at - candidate.received_at)
        return delta <= timedelta(days=days)

    def _is_continuation(self, candidate_text: str, current_text: str) -> bool:
        """
        Return True when the current text clearly extends the candidate.
        """
        if candidate_text == current_text:
            return True

        if candidate_text not in current_text:
            return False

        extra_length = len(current_text) - len(candidate_text)
        minimum_extra = max(
            self.MIN_TEXT_EXTENSION,
            int(len(candidate_text) * self.MIN_TEXT_EXTENSION_RATIO),
        )
        return extra_length >= minimum_extra

    def _is_strong_containment(
        self, candidate_text: str, current_text: str
    ) -> bool:
        """
        Return True when the current text substantially contains candidate.
        """
        if not self._is_continuation(candidate_text, current_text):
            return False

        if len(candidate_text) < 120:
            return False

        return self._containment_score(candidate_text, current_text) >= 0.38

    def _containment_score(
        self, candidate_text: str, current_text: str
    ) -> float:
        """
        Score containment strength using the relative text sizes.
        """
        if not current_text:
            return 0.0
        return len(candidate_text) / len(current_text)

    def _mark_source_as_merged(
        self,
        source: EmailMessage,
        canonical: EmailMessage,
        reason: str,
        merged_at,
    ) -> None:
        """
        Mark an older source record as merged into the canonical record.
        """
        logger.info(
            "[EmailMerge] mark source merged source_id=%s source_uuid=%s canonical_id=%s canonical_uuid=%s reason=%s",
            source.id,
            source.uuid,
            canonical.id,
            canonical.uuid,
            reason,
        )

        source.merged_into = canonical
        source.merge_reason = reason
        source.last_merged_at = merged_at
        source.save(
            update_fields=[
                "merged_into",
                "merge_reason",
                "last_merged_at",
                "updated_at",
            ]
        )

    def _mark_canonical(self, email: EmailMessage) -> None:
        """
        Mark a record as canonical if it is not merged into another record.
        """
        email.merged_into = None
        email.merge_reason = ""
        email.save(
            update_fields=[
                "merged_into",
                "merge_reason",
                "updated_at",
            ]
        )

    def _normalize_subject(self, subject: str) -> str:
        subject = subject or ""
        subject = SUBJECT_PREFIX_PATTERN.sub("", subject)
        subject = subject.strip().lower()
        return WHITESPACE_PATTERN.sub(" ", subject)

    def _normalize_text(self, content: str) -> str:
        content = content or ""
        content = re.sub(r"(?m)^\s*>.*$", "", content)
        content = re.sub(r"(?m)^-----.*?-----$", "", content)
        content = content.replace("\r", "\n")
        content = WHITESPACE_PATTERN.sub(" ", content)
        return content.strip().lower()

    def _subject_looks_forward(self, subject: str) -> bool:
        """
        Return True when the subject looks like a forwarded thread.
        """
        subject = subject or ""
        return bool(re.match(r"^\s*(fw|fwd)\s*:", subject, re.I))

    def _extract_message_tokens(self, value: str) -> list[str]:
        """
        Extract RFC message IDs from a header value.
        """
        if not value:
            return []
        return [match.group(1).strip() for match in THREAD_HEADER_PATTERN.finditer(value)]

    def _extract_reference_tokens(self, references) -> list[str]:
        """
        Normalize References header values.
        """
        if not references:
            return []
        if isinstance(references, list):
            values = references
        else:
            values = [str(references)]
        tokens: list[str] = []
        for value in values:
            tokens.extend(self._extract_message_tokens(value))
        return tokens
