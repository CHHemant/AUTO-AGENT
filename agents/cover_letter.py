"""
CoverLetterAgent
================
Role    : Generate a compelling, personalised cover letter for each opportunity.
Input   : ResumeData + InternshipOpportunity + TailoredResume content
Output  : CoverLetter (content string + path to DOCX file)
Decision: Adapts tone and emphasis based on country (e.g. formal for Germany /
          Japan, concise for USA/Canada) and research area.
"""

from __future__ import annotations

import os

from config import OUTPUT_DIR
from models import CoverLetter, InternshipOpportunity, ResumeData, TailoredResume, UserProfile
from utils.file_handler import FileHandler
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)

# Country-specific tone guidance injected into the system prompt.
_TONE_GUIDE: dict[str, str] = {
    "usa":         "Concise, confident, and results-oriented. One page strictly.",
    "canada":      "Professional yet warm. Highlight collaborative work and impact.",
    "germany":     "Formal and structured. Mention academic titles precisely. Two pages OK.",
    "france":      "Formal. Include a brief personal introduction. Français may impress.",
    "switzerland": "Precise and professional. Highlight technical depth.",
    "netherlands": "Direct and practical. Focus on concrete contributions.",
    "sweden":      "Conversational yet professional. Highlight teamwork.",
    "uk":          "Professional, concise. Avoid fluff. One page.",
    "australia":   "Friendly and results-focused. One page.",
    "japan":       "Very formal. Show respect for the research group's work specifically.",
    "singapore":   "Professional. Highlight international experience if available.",
    "default":     "Professional, concise, and tailored to the research role.",
}

_SYSTEM_PROMPT_TEMPLATE = """
You are an expert academic and research cover-letter writer.

Tone guidance for {country}: {tone}

Write a compelling cover letter that:
1. Opens with the specific role and why the applicant is excited about THIS group/lab.
2. Highlights 2–3 most relevant experiences/skills from the resume.
3. Demonstrates awareness of the organisation's research focus.
4. Closes with a professional call to action.
5. Is addressed "Dear Hiring Manager / Professor [Name if provided]".
6. Does NOT exceed {max_words} words.
7. Uses plain text – no markdown, no tables.

Output ONLY the cover letter text.
"""

_WORD_LIMITS: dict[str, int] = {
    "germany": 500, "japan": 450, "france": 500, "default": 380,
}


class CoverLetterAgent:
    """Generates personalised cover letters."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._fh = FileHandler()

    # ------------------------------------------------------------------
    def generate(
        self,
        resume: ResumeData,
        opportunity: InternshipOpportunity,
        tailored_resume: TailoredResume,
        profile: UserProfile | None = None,
    ) -> CoverLetter:
        """
        Generate a cover letter for *opportunity*.

        Parameters
        ----------
        resume          : Parsed applicant profile.
        opportunity     : Target internship.
        tailored_resume : ATS-tailored resume content for this opportunity.
        profile         : Optional applicant profile with LinkedIn URL and
                          other application details to include in the letter.
        """
        log.info(
            "[bold]CoverLetterAgent[/] – writing letter for [cyan]%s[/] @ %s",
            opportunity.title,
            opportunity.organization,
        )

        country_key = opportunity.country.lower()
        tone = _TONE_GUIDE.get(country_key, _TONE_GUIDE["default"])
        max_words = _WORD_LIMITS.get(country_key, _WORD_LIMITS["default"])

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            country=opportunity.country,
            tone=tone,
            max_words=max_words,
        )

        user_prompt = self._build_prompt(resume, opportunity, tailored_resume, profile)
        content = self._llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_key="cover_letter",
        )

        # Persist
        safe_org = FileHandler.sanitise_filename(opportunity.organization[:30])
        safe_title = FileHandler.sanitise_filename(opportunity.title[:40])
        filename = f"cover_letter_{safe_org}_{safe_title}.docx"
        file_path = os.path.join(OUTPUT_DIR, opportunity.job_id, filename)
        self._fh.save_docx(content, file_path)

        return CoverLetter(
            opportunity_id=opportunity.job_id,
            content=content,
            file_path=file_path,
        )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _build_prompt(
        resume: ResumeData,
        opportunity: InternshipOpportunity,
        tailored_resume: TailoredResume,
        profile: UserProfile | None = None,
    ) -> str:
        parts = [
            f"## Applicant\nName: {resume.full_name}\nEmail: {resume.email}\n",
        ]
        if profile:
            if profile.linkedin_url:
                parts.append(f"LinkedIn: {profile.linkedin_url}\n")
            if profile.github_url:
                parts.append(f"GitHub: {profile.github_url}\n")
            if profile.portfolio_url:
                parts.append(f"Portfolio: {profile.portfolio_url}\n")
            if profile.work_authorization:
                parts.append(f"Work Authorisation: {profile.work_authorization}\n")
            if profile.location_preference:
                parts.append(f"Location Preference: {profile.location_preference}\n")
            if profile.notice_period:
                parts.append(f"Notice Period: {profile.notice_period}\n")
            if profile.additional_notes:
                parts.append(f"Additional Notes: {profile.additional_notes}\n")
        parts += [
            f"\n## Target Role\n{opportunity.title} at {opportunity.organization}, "
            f"{opportunity.city}, {opportunity.country}\n"
            f"Research area: {opportunity.research_area}\n\n"
            f"## Job Description\n{opportunity.description}\n\n"
            f"## Tailored Resume Highlights\n{tailored_resume.content[:3000]}\n",
        ]
        return "".join(parts)
