"""Tests for CoverLetterAgent."""

import os
import pytest

from agents.cover_letter import CoverLetterAgent
from models import CoverLetter, InternshipOpportunity, ResumeData, TailoredResume
from utils.llm_client import LLMClient


class TestCoverLetterAgent:
    def test_generate_returns_cover_letter(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = CoverLetterAgent(llm=mock_llm)
        result = agent.generate(sample_resume, sample_opportunity, sample_tailored_resume)
        assert isinstance(result, CoverLetter)

    def test_generate_content_not_empty(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = CoverLetterAgent(llm=mock_llm)
        result = agent.generate(sample_resume, sample_opportunity, sample_tailored_resume)
        assert result.content.strip()

    def test_generate_creates_docx(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = CoverLetterAgent(llm=mock_llm)
        result = agent.generate(sample_resume, sample_opportunity, sample_tailored_resume)
        assert os.path.exists(result.file_path)

    def test_generate_sets_opportunity_id(
        self,
        mock_llm: LLMClient,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        import config  # noqa: PLC0415
        config.OUTPUT_DIR = str(tmp_path)
        agent = CoverLetterAgent(llm=mock_llm)
        result = agent.generate(sample_resume, sample_opportunity, sample_tailored_resume)
        assert result.opportunity_id == sample_opportunity.job_id

    def test_build_prompt_includes_applicant_name(
        self,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
    ) -> None:
        prompt = CoverLetterAgent._build_prompt(
            sample_resume, sample_opportunity, sample_tailored_resume
        )
        assert sample_resume.full_name in prompt

    def test_build_prompt_includes_organisation(
        self,
        sample_resume: ResumeData,
        sample_opportunity: InternshipOpportunity,
        sample_tailored_resume: TailoredResume,
    ) -> None:
        prompt = CoverLetterAgent._build_prompt(
            sample_resume, sample_opportunity, sample_tailored_resume
        )
        assert sample_opportunity.organization in prompt
