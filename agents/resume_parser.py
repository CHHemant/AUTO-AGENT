"""
ResumeParserAgent
=================
Role    : Extract structured data from the applicant's raw resume text.
Input   : Raw resume text (str)
Output  : ResumeData dataclass
Decision: Uses an LLM to parse free-form text into a JSON schema; falls back to
          regex-based extraction if the LLM output cannot be parsed as JSON.
"""

from __future__ import annotations

import json
import re

from models import ResumeData
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """
You are a precise resume parser. Given the text of a resume, return ONLY a valid
JSON object with the following keys (all values optional if not present):

{
  "full_name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "education": [{"degree": "", "institution": "", "year": ""}],
  "experience": [{"title": "", "org": "", "duration": "", "description": ""}],
  "skills": [],
  "publications": [],
  "projects": [{"name": "", "description": ""}],
  "certifications": [],
  "languages": []
}

Do NOT include any text outside the JSON object.
"""


class ResumeParserAgent:
    """Parses a raw resume into structured ResumeData."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    # ------------------------------------------------------------------
    def parse(self, raw_text: str) -> ResumeData:
        """
        Parse *raw_text* and return a populated :class:`ResumeData`.

        Raises
        ------
        ValueError
            If the LLM produces output that cannot be decoded as JSON and the
            regex fallback also fails to extract a name/email.
        """
        log.info("[bold]ResumeParserAgent[/] – parsing resume (%d chars)…", len(raw_text))

        llm_output = self._llm.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=raw_text[:8000],  # stay within context window
            task_key="parse_resume",
        )

        data = self._parse_json(llm_output)
        if data is None:
            log.warning("LLM JSON parse failed – falling back to regex extraction.")
            data = self._regex_fallback(raw_text)

        resume = ResumeData(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", ""),
            summary=data.get("summary", ""),
            education=data.get("education", []),
            experience=data.get("experience", []),
            skills=data.get("skills", []),
            publications=data.get("publications", []),
            projects=data.get("projects", []),
            certifications=data.get("certifications", []),
            languages=data.get("languages", []),
            raw_text=raw_text,
        )
        log.info(
            "Parsed: name=%s  skills=%d  education=%d  experience=%d",
            resume.full_name,
            len(resume.skills),
            len(resume.education),
            len(resume.experience),
        )
        return resume

    # ------------------------------------------------------------------  helpers
    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Attempt to extract and decode a JSON object from *text*."""
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the outermost {...} block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _regex_fallback(text: str) -> dict:
        """Minimal regex-based extraction when LLM JSON is unavailable."""
        result: dict = {k: [] for k in ("education", "experience", "skills",
                                         "publications", "projects",
                                         "certifications", "languages")}
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
        result["email"] = email_match.group() if email_match else ""

        phone_match = re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)
        result["phone"] = phone_match.group().strip() if phone_match else ""

        # First non-empty line likely contains the candidate's name
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not re.search(r"@|https?://|linkedin|github", stripped, re.I):
                result["full_name"] = stripped[:80]
                break

        # Skills: look for a "Skills" section and grab comma/pipe separated words
        skills_match = re.search(
            r"(?i)skills[:\s]+([^\n]{5,300})", text
        )
        if skills_match:
            raw_skills = re.split(r"[,|•·]", skills_match.group(1))
            result["skills"] = [s.strip() for s in raw_skills if s.strip()]

        return result
