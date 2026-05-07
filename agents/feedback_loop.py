"""
FeedbackLoopAgent
=================
Role    : Evaluate the quality of generated artefacts and decide whether to
          trigger a refinement loop or accept the current output.
Input   : ATSResult + ApplicationRecord + retry_count
Output  : Decision (REFINE | ACCEPT | SKIP) + reason string
Decision tree
─────────────
1. If ATS score ≥ threshold → ACCEPT (proceed to submission).
2. If ATS score < threshold AND retry_count < max_retries → REFINE
   (return control to orchestrator which re-runs ResumeTailor + ATSScorer).
3. If retry_count ≥ max_retries → SKIP (log warning, mark as skipped to avoid
   infinite loops).
"""

from __future__ import annotations

from enum import Enum

from config import ATS_MAX_RETRIES, ATS_PASS_THRESHOLD
from models import ApplicationRecord, ApplicationStatus, ATSResult
from utils.logger import get_logger

log = get_logger(__name__)


class FeedbackDecision(str, Enum):
    ACCEPT = "accept"
    REFINE = "refine"
    SKIP   = "skip"


class FeedbackLoopAgent:
    """
    Evaluates quality and drives the refinement loop.

    The agent follows a deterministic decision tree (no LLM call needed here)
    to keep latency low on the hot path.
    """

    def __init__(
        self,
        pass_threshold: int = ATS_PASS_THRESHOLD,
        max_retries: int = ATS_MAX_RETRIES,
    ) -> None:
        self._threshold = pass_threshold
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    def evaluate(
        self,
        record: ApplicationRecord,
        ats_result: ATSResult,
    ) -> tuple[FeedbackDecision, str]:
        """
        Decide whether to ACCEPT, REFINE, or SKIP the current application.

        Parameters
        ----------
        record     : Current application record (contains retry_count).
        ats_result : Latest ATS scoring result.

        Returns
        -------
        (FeedbackDecision, reason_string)
        """
        score = ats_result.score
        retries = record.retry_count

        log.info(
            "[bold]FeedbackLoopAgent[/] – score=%d  threshold=%d  retries=%d/%d",
            score,
            self._threshold,
            retries,
            self._max_retries,
        )

        if score >= self._threshold:
            reason = (
                f"ATS score {score} ≥ threshold {self._threshold}. "
                "Resume accepted."
            )
            log.info("[green]Decision: ACCEPT[/] – %s", reason)
            record.ats_result = ats_result
            record.status = ApplicationStatus.ATS_PASSED
            return FeedbackDecision.ACCEPT, reason

        if retries < self._max_retries:
            reason = (
                f"ATS score {score} < threshold {self._threshold}. "
                f"Retry {retries + 1}/{self._max_retries}. "
                f"Missing: {', '.join(ats_result.missing_keywords[:3])}."
            )
            log.warning("[yellow]Decision: REFINE[/] – %s", reason)
            record.retry_count += 1
            return FeedbackDecision.REFINE, reason

        # Max retries exceeded
        reason = (
            f"ATS score {score} still below threshold after "
            f"{self._max_retries} retries. Skipping this opportunity."
        )
        log.warning("[red]Decision: SKIP[/] – %s", reason)
        record.status = ApplicationStatus.SKIPPED
        record.error_message = reason
        return FeedbackDecision.SKIP, reason
