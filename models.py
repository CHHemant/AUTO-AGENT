"""
Data models shared across all agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    RESUME_PARSED = "resume_parsed"
    JOBS_FOUND = "jobs_found"
    RESUME_TAILORED = "resume_tailored"
    COVER_LETTER_DONE = "cover_letter_done"
    ATS_PASSED = "ats_passed"
    SUBMITTED = "submitted"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ResumeData:
    """Structured representation of an applicant's resume."""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    education: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    publications: list[str] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class InternshipOpportunity:
    """Represents a single internship opportunity."""
    job_id: str = ""
    title: str = ""
    organization: str = ""
    country: str = ""
    city: str = ""
    description: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    application_url: str = ""
    deadline: str = ""
    duration: str = ""
    stipend: str = ""
    research_area: str = ""
    source: str = ""


@dataclass
class TailoredResume:
    """ATS-optimised resume for a specific opportunity."""
    opportunity_id: str = ""
    content: str = ""        # Markdown/plain text representation
    file_path: str = ""      # Path to generated DOCX
    keywords_added: list[str] = field(default_factory=list)
    ats_score: int = 0


@dataclass
class CoverLetter:
    """Cover letter generated for a specific opportunity."""
    opportunity_id: str = ""
    content: str = ""
    file_path: str = ""


@dataclass
class ATSResult:
    """Result of ATS scoring for a resume against a job description."""
    score: int = 0                              # 0–100
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    passed: bool = False


@dataclass
class ApplicationRecord:
    """Full record of one job application lifecycle."""
    opportunity: InternshipOpportunity = field(default_factory=InternshipOpportunity)
    tailored_resume: Optional[TailoredResume] = None
    cover_letter: Optional[CoverLetter] = None
    ats_result: Optional[ATSResult] = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    error_message: str = ""
    retry_count: int = 0
