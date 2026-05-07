"""
ResumeTailoringAgent
====================
Role    : Produce an ATS-friendly, role-specific resume for a given opportunity.
Input   : ResumeData + InternshipOpportunity (+ optional ATS feedback)
Output  : TailoredResume (content string + path to DOCX file)
Decision: Instructs the LLM to re-order sections, add missing keywords from the
          job description, and emphasise relevant experience.
          On retry (ATS score too low) the feedback from ATSScorerAgent is
          injected into the prompt so the model can address specific gaps.
"""

from __future__ import annotations

import os

from config import OUTPUT_DIR
from models import ATSResult, InternshipOpportunity, ResumeData, TailoredResume
from utils.file_handler import FileHandler
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """
You are an expert resume writer who specialises in ATS (Applicant Tracking System)
optimisation for research internship applications.

Your task:
1. Rewrite the provided resume to maximise ATS compatibility for the target job.
2. Mirror keywords from the job description naturally into the resume text.
3. Prioritise sections most relevant to the role (e.g. publications, research
   experience, relevant projects).
4. Use clean, standard section headings: CONTACT, SUMMARY, EDUCATION, RESEARCH
   EXPERIENCE, SKILLS, PUBLICATIONS, PROJECTS, CERTIFICATIONS.
5. Avoid tables, columns, headers/footers, images, or special characters.
6. Keep the resume to one or two pages.

Output ONLY the resume text – no commentary, no JSON, no markdown fences.
"""


class ResumeTailoringAgent:
    """Creates ATS-optimised, role-specific resumes."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._fh = FileHandler()

    # ------------------------------------------------------------------
    def tailor(
        self,
        resume: ResumeData,
        opportunity: InternshipOpportunity,
        ats_feedback: ATSResult | None = None,
    ) -> TailoredResume:
        """
        Produce a tailored resume for *opportunity*.

        Parameters
        ----------
        resume       : Parsed applicant profile.
        opportunity  : Target internship.
        ats_feedback : Optional feedback from a previous ATS scoring round.
        """
        log.info(
            "[bold]ResumeTailoringAgent[/] – tailoring for [cyan]%s[/] @ %s",
            opportunity.title,
            opportunity.organization,
        )

        user_prompt = self._build_prompt(resume, opportunity, ats_feedback)
        content = self._llm.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            task_key="tailor_resume",
        )

        # Persist to DOCX
        safe_org = FileHandler.sanitise_filename(opportunity.organization[:30])
        safe_title = FileHandler.sanitise_filename(opportunity.title[:40])
        filename = f"resume_{safe_org}_{safe_title}.docx"
        file_path = os.path.join(OUTPUT_DIR, opportunity.job_id, filename)
        self._fh.save_docx(content, file_path)

        # Detect which job-description keywords appear in the new content
        jd_keywords = opportunity.required_skills + opportunity.preferred_skills
        added = [kw for kw in jd_keywords if kw.lower() in content.lower()]

        return TailoredResume(
            opportunity_id=opportunity.job_id,
            content=content,
            file_path=file_path,
            keywords_added=added,
        )

    # ------------------------------------------------------------------  helpers
    @staticmethod
    def _build_prompt(
        resume: ResumeData,
        opportunity: InternshipOpportunity,
        ats_feedback: ATSResult | None,
    ) -> str:
        parts = [
            f"## Target Role\nTitle: {opportunity.title}\n"
            f"Organisation: {opportunity.organization} ({opportunity.country})\n"
            f"Research Area: {opportunity.research_area}\n",
            f"## Job Description\n{opportunity.description}\n",
            f"## Required Skills\n{', '.join(opportunity.required_skills)}\n",
            f"## Preferred Skills\n{', '.join(opportunity.preferred_skills)}\n",
            f"## Applicant's Current Resume\n{resume.raw_text[:6000]}\n",
        ]
        if ats_feedback:
            parts.append(
                f"## ATS Feedback (previous score: {ats_feedback.score}/100)\n"
                f"Missing keywords: {', '.join(ats_feedback.missing_keywords)}\n"
                + "\n".join(f"- {s}" for s in ats_feedback.suggestions)
            )
        return "\n".join(parts)
