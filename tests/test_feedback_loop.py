"""Tests for FeedbackLoopAgent."""

import pytest

from agents.feedback_loop import FeedbackDecision, FeedbackLoopAgent
from models import ApplicationRecord, ApplicationStatus, ATSResult, InternshipOpportunity


def _make_record(retry_count: int = 0) -> ApplicationRecord:
    return ApplicationRecord(
        opportunity=InternshipOpportunity(job_id="t1", title="Test Role"),
        status=ApplicationStatus.RESUME_TAILORED,
        retry_count=retry_count,
    )


def _ats(score: int, passed: bool = False) -> ATSResult:
    return ATSResult(
        score=score,
        matched_keywords=["Python"],
        missing_keywords=["PyTorch"],
        suggestions=["Add PyTorch."],
        passed=passed,
    )


class TestFeedbackLoopAgent:
    def test_accept_when_score_above_threshold(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=3)
        record = _make_record()
        decision, reason = agent.evaluate(record, _ats(80))
        assert decision == FeedbackDecision.ACCEPT
        assert record.status == ApplicationStatus.ATS_PASSED

    def test_refine_when_score_below_threshold_and_retries_available(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=3)
        record = _make_record(retry_count=0)
        decision, _ = agent.evaluate(record, _ats(50))
        assert decision == FeedbackDecision.REFINE
        assert record.retry_count == 1

    def test_skip_when_max_retries_exceeded(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=3)
        record = _make_record(retry_count=3)
        decision, _ = agent.evaluate(record, _ats(40))
        assert decision == FeedbackDecision.SKIP
        assert record.status == ApplicationStatus.SKIPPED

    def test_retry_count_increments_on_refine(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=5)
        record = _make_record(retry_count=1)
        agent.evaluate(record, _ats(60))
        assert record.retry_count == 2

    def test_ats_result_stored_on_accept(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=3)
        record = _make_record()
        ats = _ats(90, passed=True)
        agent.evaluate(record, ats)
        assert record.ats_result is ats

    def test_threshold_boundary_exact_value(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=75, max_retries=3)
        record = _make_record()
        decision, _ = agent.evaluate(record, _ats(75))
        assert decision == FeedbackDecision.ACCEPT

    def test_custom_threshold(self) -> None:
        agent = FeedbackLoopAgent(pass_threshold=90, max_retries=2)
        record = _make_record()
        decision, _ = agent.evaluate(record, _ats(89))
        assert decision == FeedbackDecision.REFINE
