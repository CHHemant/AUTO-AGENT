"""Tests for ATSScorerAgent."""

import json
import pytest

from agents.ats_scorer import ATSScorerAgent
from models import ATSResult, InternshipOpportunity, TailoredResume
from utils.llm_client import LLMClient


class TestATSScorerAgent:
    def test_score_returns_ats_result(
        self,
        mock_llm: LLMClient,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        agent = ATSScorerAgent(llm=mock_llm)
        result = agent.score(sample_tailored_resume, sample_opportunity)
        assert isinstance(result, ATSResult)

    def test_score_range(
        self,
        mock_llm: LLMClient,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        agent = ATSScorerAgent(llm=mock_llm)
        result = agent.score(sample_tailored_resume, sample_opportunity)
        assert 0 <= result.score <= 100

    def test_passed_flag_set_correctly(
        self,
        mock_llm: LLMClient,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        agent = ATSScorerAgent(llm=mock_llm)
        result = agent.score(sample_tailored_resume, sample_opportunity)
        # Mock returns score=82 which is >= default threshold of 75
        assert result.passed is True

    def test_parse_result_valid_json(
        self,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        raw = json.dumps({
            "score": 90,
            "matched_keywords": ["Python"],
            "missing_keywords": [],
            "suggestions": [],
        })
        result = ATSScorerAgent._parse_result(raw, sample_tailored_resume, sample_opportunity)
        assert result.score == 90
        assert result.matched_keywords == ["Python"]

    def test_parse_result_clamps_score(
        self,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        raw = json.dumps({"score": 150, "matched_keywords": [], "missing_keywords": [], "suggestions": []})
        result = ATSScorerAgent._parse_result(raw, sample_tailored_resume, sample_opportunity)
        assert result.score == 100

    def test_parse_result_invalid_json_falls_back(
        self,
        sample_tailored_resume: TailoredResume,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        result = ATSScorerAgent._parse_result(
            "not valid json", sample_tailored_resume, sample_opportunity
        )
        assert isinstance(result, ATSResult)
        assert 0 <= result.score <= 100

    def test_rule_based_score_all_keywords_present(self) -> None:
        resume = TailoredResume(
            opportunity_id="x",
            content="Python PyTorch NLP deep learning",
        )
        opp = InternshipOpportunity(
            job_id="x",
            required_skills=["Python", "PyTorch"],
            preferred_skills=["NLP"],
        )
        result = ATSScorerAgent._rule_based_score(resume, opp)
        assert result.score == 100

    def test_rule_based_score_no_keywords(self) -> None:
        resume = TailoredResume(opportunity_id="x", content="I am a researcher.")
        opp = InternshipOpportunity(
            job_id="x",
            required_skills=["Python"],
            preferred_skills=["PyTorch"],
        )
        result = ATSScorerAgent._rule_based_score(resume, opp)
        assert result.score == 0

    def test_rule_based_score_no_jd_keywords(self) -> None:
        resume = TailoredResume(opportunity_id="x", content="Some text.")
        opp = InternshipOpportunity(job_id="x", required_skills=[], preferred_skills=[])
        result = ATSScorerAgent._rule_based_score(resume, opp)
        assert result.score == 50  # neutral when no keywords defined
