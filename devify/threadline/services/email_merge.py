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
    evidence: Optional[dict] = None

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
    # Below this normalized-text length, fuzzy similarity is unreliable
    # (image-heavy emails with a one-line note over-trigger the thresholds),
    # so require exact equality instead of trusting RapidFuzz.
    MIN_TEXT_SIMILARITY_LENGTH = 120

    def decide(self, email: EmailMessage) -> MergeDecision:
        """
        Find a related target for the given email if mergeable.
        """
        logger.info(
            f"[EmailMerge] decide start email_id={email.id} uuid={email.uuid}"
            f" subject={email.subject!r} received_at={email.received_at}"
            f" status={email.status} merged_into_id={email.merged_into_id}"
        )
        if email.merged_into_id:
            # Once a record already has a relation, keep following that
            # relation instead of re-deciding against the candidate set.
            canonical = self.resolve_canonical(email)
            logger.info(
                f"[EmailMerge] decide short-circuit email_id={email.id}"
                f" target_id={canonical.id} target_uuid={canonical.uuid}"
                f" reason={email.merge_reason}"
            )
            return MergeDecision(target=canonical, reason=email.merge_reason)

        # Find older canonical candidates that appear to belong to the same
        # conversation cluster as the current email.
        matched_sources = self._find_merge_sources(email)
        logger.info(
            f"[EmailMerge] decide matched_sources email_id={email.id}"
            f" matched_source_ids={[s.id for s in matched_sources]}"
        )
        if matched_sources:
            # Pick the earliest matching record as a stable relation anchor.
            target = self._select_merge_target(matched_sources)
            merge_reason = self._determine_merge_reason(
                email, matched_sources
            )
            # Collect evidence once, against the source that actually drove the
            # chosen reason, so it can never disagree with merge_reason and is
            # never empty for a genuine merge.
            primary_source = self._primary_source(
                email, matched_sources, merge_reason
            )
            evidence = self._collect_evidence(
                email, primary_source, merge_reason
            )
            logger.info(
                f"[EmailMerge] decide target email_id={email.id}"
                f" target_id={target.id} target_uuid={target.uuid}"
                f" reason={merge_reason} evidence={evidence}"
            )
            return MergeDecision(
                target=target,
                reason=merge_reason,
                sources=tuple(matched_sources),
                evidence=evidence,
            )

        return MergeDecision(target=None)

    def reconcile(
        self, email: EmailMessage
    ) -> tuple[EmailMessage, MergeDecision]:
        """
        Apply the merge decision and return the canonical record.

        The newest record in a cluster is kept as the canonical anchor: an
        arriving email absorbs the older matching records instead of being
        hidden behind them, so a new email's own content is never lost. Manual
        merges stay authoritative, so an email matching a manual canonical is
        linked into it rather than absorbing it.
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
            target_id = getattr(decision.target, "id", None)
            target_uuid = getattr(decision.target, "uuid", None)
            source_ids = [s.id for s in decision.sources]
            logger.info(
                f"[EmailMerge] reconcile decision email_id={email.id}"
                f" should_merge={decision.should_merge}"
                f" target_id={target_id} target_uuid={target_uuid}"
                f" source_ids={source_ids} reason={decision.reason}"
            )

            if not (decision.should_merge and decision.sources):
                self._mark_canonical(email)
                return email, decision

            merged_at = timezone.now()
            cluster_heads = self._distinct_cluster_heads(
                email, decision.sources
            )

            # Manual merges are authoritative: an arriving email that matches a
            # manual canonical is linked into it instead of absorbing it.
            manual_head = next(
                (
                    head
                    for head in cluster_heads
                    if self._is_manual_canonical(head)
                ),
                None,
            )
            if manual_head is not None:
                target = EmailMessage.objects.select_for_update().get(
                    pk=manual_head.pk
                )
                self._mark_source_as_merged(
                    email, target, decision.reason, merged_at,
                    decision.evidence,
                )
                return target, decision

            # Otherwise keep the newest record (the arriving email) as the
            # canonical anchor and absorb the older cluster heads into it.
            self._mark_canonical(email)
            for head in cluster_heads:
                locked_head = EmailMessage.objects.select_for_update().get(
                    pk=head.pk
                )
                if locked_head.merged_into_id == email.pk:
                    continue
                self._mark_source_as_merged(
                    locked_head, email, decision.reason, merged_at,
                    decision.evidence,
                )
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
                    f"Detected circular merge chain for email {current.pk}"
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
                f"[EmailMerge] candidate scan email_id={email.id}"
                f" candidate_id={candidate.id}"
                f" candidate_uuid={candidate.uuid}"
                f" subject={candidate.subject!r}"
                f" received_at={candidate.received_at}"
                f" status={candidate.status}"
            )
            if self._candidate_matches(email, candidate):
                matched_sources.append(candidate)
                logger.debug(
                    f"[EmailMerge] candidate matched email_id={email.id}"
                    f" candidate_id={candidate.id}"
                )
            else:
                logger.debug(
                    f"[EmailMerge] candidate not matched email_id={email.id}"
                    f" candidate_id={candidate.id}"
                )
        return matched_sources

    def _select_merge_target(
        self, sources: Iterable[EmailMessage]
    ) -> EmailMessage:
        """
        Choose a deterministic relation anchor within the related cluster.
        """
        candidates = list(sources)
        candidate_ids = [item.id for item in candidates]
        candidate_details = [
            {
                "id": item.id,
                "uuid": str(item.uuid),
                "received_at": item.received_at.isoformat()
                if item.received_at
                else None,
            }
            for item in candidates
        ]
        logger.info(
            f"[EmailMerge] select target cluster"
            f" candidate_ids={candidate_ids}"
            f" received_at={candidate_details}"
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
                f"[EmailMerge] matcher hit thread_relation"
                f" email_id={email.id} candidate_id={candidate.id}"
            )
            return True
        # The matchers only compare text; for image-heavy emails the real
        # content lives in the images. When both records carry images and the
        # image sets are completely different, the content-based signals below
        # are not trustworthy, so block the merge. This is intentional: a
        # recurring series with the same boilerplate text but a fresh image
        # each time is kept as separate conversations rather than fused.
        # Thread-header matches above stay authoritative (a genuine reply with
        # a new screenshot still merges via In-Reply-To/References).
        if self._has_disjoint_images(email, candidate):
            logger.debug(
                f"[EmailMerge] blocked by disjoint images"
                f" email_id={email.id} candidate_id={candidate.id}"
            )
            return False
        if self._matches_forward_chain(email, candidate):
            logger.debug(
                f"[EmailMerge] matcher hit forward_chain"
                f" email_id={email.id} candidate_id={candidate.id}"
            )
            return True
        if self._matches_text_similarity(email, candidate):
            logger.debug(
                f"[EmailMerge] matcher hit text_similarity"
                f" email_id={email.id} candidate_id={candidate.id}"
            )
            return True
        if self._matches_containment(email, candidate):
            logger.debug(
                f"[EmailMerge] matcher hit containment"
                f" email_id={email.id} candidate_id={candidate.id}"
            )
            return True
        logger.debug(
            f"[EmailMerge] matcher miss"
            f" email_id={email.id} candidate_id={candidate.id}"
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
            candidate_ids.extend(
                self._extract_message_tokens(email.in_reply_to)
            )
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

        # A forward is already a strong signal (Fwd prefix + identical
        # subject), so do not apply the short-text length floor here; the
        # floor exists only to keep the weaker text_similarity path from
        # over-matching on tiny bodies.
        return self._text_bodies_match(
            email, candidate, apply_length_floor=False
        )

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

        return self._text_bodies_match(
            email, candidate, apply_length_floor=True
        )

    def _text_bodies_match(
        self,
        email: EmailMessage,
        candidate: EmailMessage,
        apply_length_floor: bool,
    ) -> bool:
        """
        Compare the two records' extracted text bodies.

        Keep the heuristic simple and predictable: only compare raw extracted
        text; if a record has no text_content, skip it instead of inferring
        from HTML. When ``apply_length_floor`` is set, short bodies (e.g. an
        image plus a one-line note or a shared signature/footer) make RapidFuzz
        unreliable, so require exact normalized-text equality below the length
        floor instead of a fuzzy score.
        """
        current_text = self._normalize_text(email.text_content)
        candidate_text = self._normalize_text(candidate.text_content)
        if not current_text or not candidate_text:
            return False

        if (
            apply_length_floor
            and min(len(current_text), len(candidate_text))
            < self.MIN_TEXT_SIMILARITY_LENGTH
        ):
            return current_text == candidate_text

        ratio, partial_ratio = self._text_similarity_scores(
            candidate_text, current_text
        )
        logger.debug(
            f"[EmailMerge] rapidfuzz similarity email_id={email.id}"
            f" candidate_id={candidate.id}"
            f" ratio={ratio:.2f} partial_ratio={partial_ratio:.2f}"
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

    def _image_md5_set(self, email: EmailMessage) -> set:
        """
        Content MD5s of this record's image attachments (empty if none).

        Queried lazily and cached on the model instance so the arriving email
        is fetched at most once and each candidate at most once. Only reached
        when the arriving email itself has images (see _has_disjoint_images),
        so mailboxes without image attachments never hit this query.
        """
        cached = getattr(email, "_merge_image_md5s", None)
        if cached is not None:
            return cached
        result = {
            att.content_md5
            for att in email.attachments.all()
            if att.is_image and att.content_md5
        }
        email._merge_image_md5s = result
        return result

    def _has_disjoint_images(
        self, email: EmailMessage, candidate: EmailMessage
    ) -> bool:
        """
        True when both records have image attachments and their content MD5
        sets do not overlap at all.

        Returns False (do not block) when either side has no comparable image
        MD5s, so records without images fall through to normal matching.
        """
        email_images = self._image_md5_set(email)
        if not email_images:
            return False
        candidate_images = self._image_md5_set(candidate)
        if not candidate_images:
            return False
        return email_images.isdisjoint(candidate_images)

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
        return sorted(
            materialized, key=lambda item: (item.received_at, item.id)
        )[0]

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

    def _primary_source(
        self,
        email: EmailMessage,
        sources: list[EmailMessage],
        reason: str,
    ) -> Optional[EmailMessage]:
        """
        Pick the matched source whose own match reason equals the cluster's
        chosen (strongest) reason.

        This ties the persisted evidence to the exact source/signal that
        produced ``merge_reason``, so the two can never disagree. Falls back to
        the first source if none matches (should not happen, since the reason
        is derived from the same source set).
        """
        for source in sources:
            if self._candidate_match_reason(email, source) == reason:
                return source
        return sources[0] if sources else None

    def _collect_evidence(
        self,
        email: EmailMessage,
        candidate: Optional[EmailMessage],
        reason: str,
    ) -> dict:
        """
        Build the discriminating evidence for the pair that drove the merge.

        ``email`` is the arriving record and ``candidate`` is the primary
        matched source. ``reason`` is the persisted merge_reason (the cluster's
        strongest category); it is always echoed as ``evidence["reason"]`` so
        the audit record can never contradict merge_reason. ``signal`` names
        the exact matcher that fired for this pair (e.g. "containment", which
        the enum folds into the text_similarity reason) as a finer detail.

        Returns a small JSON-serializable dict persisted on merged records so a
        merge can be explained after the fact without DEBUG logs.
        """
        evidence: dict = {"reason": reason}
        if candidate is None:
            return evidence

        if self._matches_thread_relation(email, candidate):
            tokens = []
            if email.in_reply_to:
                tokens.extend(self._extract_message_tokens(email.in_reply_to))
            tokens.extend(self._extract_reference_tokens(email.references))
            matched = next(
                (
                    token
                    for token in tokens
                    if token
                    in (candidate.raw_message_id, candidate.message_id)
                ),
                None,
            )
            evidence.update(
                signal="thread_relation", matched_message_id=matched
            )
            return evidence

        candidate_text = self._normalize_text(candidate.text_content)
        email_text = self._normalize_text(email.text_content)

        if self._matches_forward_chain(email, candidate):
            ratio, partial_ratio = self._text_similarity_scores(
                candidate_text, email_text
            )
            evidence.update(
                signal="forward_chain",
                ratio=round(ratio, 1),
                partial_ratio=round(partial_ratio, 1),
            )
            return evidence

        if self._matches_text_similarity(email, candidate):
            ratio, partial_ratio = self._text_similarity_scores(
                candidate_text, email_text
            )
            evidence.update(
                signal="text_similarity",
                ratio=round(ratio, 1),
                partial_ratio=round(partial_ratio, 1),
                candidate_text_len=len(candidate_text),
                email_text_len=len(email_text),
            )
            return evidence

        if self._matches_containment(email, candidate):
            evidence.update(
                signal="containment",
                candidate_text_len=len(candidate_text),
                email_text_len=len(email_text),
                containment_score=round(
                    self._containment_score(candidate_text, email_text), 3
                ),
            )
            return evidence

        # The primary source matched under a signal that no longer fires for
        # this exact pair (rare); keep the reason so the record is never empty.
        evidence["signal"] = reason
        return evidence

    def _mark_source_as_merged(
        self,
        source: EmailMessage,
        canonical: EmailMessage,
        reason: str,
        merged_at,
        evidence: Optional[dict] = None,
    ) -> None:
        """
        Mark an older source record as merged into the canonical record.
        """
        logger.info(
            f"[EmailMerge] mark source merged source_id={source.id}"
            f" source_uuid={source.uuid} canonical_id={canonical.id}"
            f" canonical_uuid={canonical.uuid} reason={reason}"
            f" evidence={evidence}"
        )

        source.merged_into = canonical
        source.merge_reason = reason
        source.merge_evidence = evidence or None
        source.last_merged_at = merged_at
        source.save(
            update_fields=[
                "merged_into",
                "merge_reason",
                "merge_evidence",
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

    def _distinct_cluster_heads(
        self, email: EmailMessage, sources: Iterable[EmailMessage]
    ) -> list[EmailMessage]:
        """
        Resolve matched records to the head of their existing merge cluster.

        Re-pointing cluster heads instead of individual leaves keeps the merge
        graph consistent when an email matches a record that was already merged
        into a canonical anchor.
        """
        heads: dict[int, EmailMessage] = {}
        for source in sources:
            head = self.resolve_canonical(source)
            if head.pk == email.pk:
                continue
            heads.setdefault(head.pk, head)
        return list(heads.values())

    def _is_manual_canonical(self, email: EmailMessage) -> bool:
        """
        Return True when a record is a manually merged canonical message.
        """
        message_id = email.message_id or ""
        return message_id.startswith("manual-merge-")

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
        return [
            match.group(1).strip()
            for match in THREAD_HEADER_PATTERN.finditer(value)
        ]

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
