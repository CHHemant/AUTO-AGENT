"""
Shared pytest fixtures used across the test suite.
"""

import pytest

from models import (
    ATSResult,
    CoverLetter,
    InternshipOpportunity,
    ResumeData,
    TailoredResume,
)
from utils.llm_client import LLMClient


# ─── Minimal sample data ──────────────────────────────────────────────────────

@pytest.fixture()
def sample_resume() -> ResumeData:
    return ResumeData(
        full_name="Alice Researcher",
        email="alice@example.com",
        phone="+1-555-0101",
        summary="PhD candidate specialising in NLP and deep learning.",
        education=[{"degree": "B.Sc. CS", "institution": "MIT", "year": "2022"}],
        experience=[{
            "title": "Research Intern",
            "org": "Google Brain",
            "duration": "Summer 2023",
            "description": "Worked on transformer models.",
        }],
        skills=["Python", "PyTorch", "NLP", "deep learning", "transformer"],
        publications=["Alice et al. (2024). Fast NLP. ArXiv."],
        projects=[{"name": "MiniGPT", "description": "Small language model."}],
        raw_text=(
            "Alice Researcher\nalice@example.com\n"
            "Skills: Python, PyTorch, NLP, deep learning, transformer\n"
            "Education: B.Sc. CS, MIT, 2022\n"
        ),
    )


@pytest.fixture()
def sample_opportunity() -> InternshipOpportunity:
    return InternshipOpportunity(
        job_id="test-job-001",
        title="NLP Research Intern",
        organization="Test Lab",
        country="Germany",
        city="Berlin",
        description="Work on transformer-based NLP models using Python and PyTorch.",
        required_skills=["Python", "PyTorch", "NLP"],
        preferred_skills=["transformer", "deep learning"],
        application_url="https://testlab.example.com/apply",
        source="sample",
    )


@pytest.fixture()
def sample_tailored_resume(sample_opportunity: InternshipOpportunity) -> TailoredResume:
    return TailoredResume(
        opportunity_id=sample_opportunity.job_id,
        content=(
            "Alice Researcher\nalice@example.com\n\n"
            "SKILLS\nPython, PyTorch, NLP, deep learning, transformer\n\n"
            "EXPERIENCE\nResearch Intern, Google Brain – Summer 2023\n"
            "Worked on transformer models.\n"
        ),
        file_path="/tmp/test_resume.docx",
        keywords_added=["Python", "PyTorch", "NLP"],
    )


@pytest.fixture()
def sample_ats_result() -> ATSResult:
    return ATSResult(
        score=82,
        matched_keywords=["Python", "PyTorch", "NLP"],
        missing_keywords=["transformer"],
        suggestions=["Add 'transformer' to skills section."],
        passed=True,
    )


@pytest.fixture()
def mock_llm() -> LLMClient:
    """Return an LLMClient that always uses mock responses."""
    # Force mock mode by ensuring no API key is configured
    import config  # noqa: PLC0415
    original = config.OPENAI_API_KEY
    config.OPENAI_API_KEY = ""
    client = LLMClient()
    config.OPENAI_API_KEY = original
    return client
