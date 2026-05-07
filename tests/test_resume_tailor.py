"""Tests for ResumeTailoringAgent."""

import os
import pytest

from agents.resume_tailor import ResumeTailoringAgent
from models import ATSResult, InternshipOpportunity, ResumeData, TailoredResume
from utils.llm_client import LLMClient


class TestResumeTailoringAgent:
    def test_tailor_returns_tailored_resume(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = ResumeTailoringAgent(llm=mock_llm)
        result = agent.tailor(sample_resume, sample_opportunity)
        assert isinstance(result, TailoredResume)

    def test_tailor_sets_opportunity_id(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = ResumeTailoringAgent(llm=mock_llm)
        result = agent.tailor(sample_resume, sample_opportunity)
        assert result.opportunity_id == sample_opportunity.job_id

    def test_tailor_content_not_empty(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = ResumeTailoringAgent(llm=mock_llm)
        result = agent.tailor(sample_resume, sample_opportunity)
        assert result.content.strip()

    def test_tailor_creates_docx_file(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = ResumeTailoringAgent(llm=mock_llm)
        result = agent.tailor(sample_resume, sample_opportunity)
        assert os.path.exists(result.file_path)

    def test_build_prompt_includes_role(
        self,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        prompt = ResumeTailoringAgent._build_prompt(sample_resume, sample_opportunity, None)
        assert sample_opportunity.title in prompt
        assert sample_opportunity.organization in prompt

    def test_build_prompt_includes_ats_feedback(
        self,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
    ) -> None:
        feedback = ATSResult(
            score=60,
            missing_keywords=["transformer"],
            suggestions=["Add transformer."],
        )
        prompt = ResumeTailoringAgent._build_prompt(sample_resume, sample_opportunity, feedback)
        assert "transformer" in prompt
        assert "60" in prompt
