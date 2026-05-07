"""
ATSScorerAgent
==============
Role    : Score a tailored resume against a job description for ATS compatibility.
Input   : TailoredResume content + InternshipOpportunity (job description +
          required/preferred skills)
Output  : ATSResult (score 0–100, matched keywords, missing keywords, suggestions)
Decision: Uses the LLM to simulate ATS keyword matching and scoring, then applies
          a rule-based floor/ceiling to keep scores realistic.
"""

from __future__ import annotations

import json
import re

from config import ATS_PASS_THRESHOLD
from models import ATSResult, InternshipOpportunity, TailoredResume
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """
You are an ATS (Applicant Tracking System) simulator.

Given a job description and a resume, evaluate how well the resume matches the
role and return ONLY a valid JSON object with these fields:

{
  "score": <integer 0–100>,
  "matched_keywords": [<list of strings>],
  "missing_keywords": [<list of strings>],
  "suggestions": [<list of actionable improvement strings>]
}

Scoring guidelines
──────────────────
• 90–100 : Excellent – nearly all key terms present, formatting is clean.
• 75–89  : Good – most terms present, minor gaps.
• 60–74  : Fair – several important terms missing.
• Below 60: Poor – significant gaps; resume needs substantial revision.

Do NOT output anything outside the JSON object.
"""


class ATSScorerAgent:
    """Scores a resume for ATS compatibility against a specific job description."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    # ------------------------------------------------------------------
    def score(
        self,
        tailored_resume: TailoredResume,
        opportunity: InternshipOpportunity,
    ) -> ATSResult:
        """
        Compute an ATS score for *tailored_resume* against *opportunity*.

        Returns
        -------
        ATSResult with score, keyword lists, and actionable suggestions.
        """
        log.info(
            "[bold]ATSScorerAgent[/] – scoring resume for [cyan]%s[/]",
            opportunity.title,
        )

        user_prompt = (
            f"## Job Description\n{opportunity.description}\n\n"
            f"## Required Skills\n{', '.join(opportunity.required_skills)}\n\n"
            f"## Preferred Skills\n{', '.join(opportunity.preferred_skills)}\n\n"
            f"## Resume Text\n{tailored_resume.content[:6000]}"
        )

        raw = self._llm.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            task_key="ats_score",
        )

        result = self._parse_result(raw, tailored_resume, opportunity)
        result.passed = result.score >= ATS_PASS_THRESHOLD

        log.info(
            "ATS score: %d/100 (%s) – matched=%d  missing=%d",
            result.score,
            "[green]PASS[/]" if result.passed else "[red]FAIL[/]",
            len(result.matched_keywords),
            len(result.missing_keywords),
        )
        return result

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _parse_result(
        raw: str,
        tailored_resume: TailoredResume,
        opportunity: InternshipOpportunity,
    ) -> ATSResult:
        """Parse LLM JSON output; fall back to rule-based scoring on error."""
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        try:
            data = json.loads(raw)
            return ATSResult(
                score=max(0, min(100, int(data.get("score", 0)))),
                matched_keywords=data.get("matched_keywords", []),
                missing_keywords=data.get("missing_keywords", []),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            log.warning("ATS score JSON parse failed – using rule-based fallback.")
            return ATSScorerAgent._rule_based_score(tailored_resume, opportunity)

    @staticmethod
    def _rule_based_score(
        tailored_resume: TailoredResume,
        opportunity: InternshipOpportunity,
    ) -> ATSResult:
        """Simple keyword-overlap scoring used when LLM output is unparseable."""
        resume_lower = tailored_resume.content.lower()
        required = opportunity.required_skills
        preferred = opportunity.preferred_skills
        all_keywords = required + preferred

        matched = [kw for kw in all_keywords if kw.lower() in resume_lower]
        missing = [kw for kw in all_keywords if kw.lower() not in resume_lower]

        if not all_keywords:
            score = 50
        else:
            # Required keywords weighted double
            req_matched = sum(1 for kw in required if kw.lower() in resume_lower)
            pref_matched = sum(1 for kw in preferred if kw.lower() in resume_lower)
            total_weight = len(required) * 2 + len(preferred)
            earned = req_matched * 2 + pref_matched
            score = int((earned / total_weight) * 100) if total_weight else 50
            score = max(0, min(100, score))

        suggestions = [f"Add '{kw}' to your resume." for kw in missing[:5]]

        return ATSResult(
            score=score,
            matched_keywords=matched,
            missing_keywords=missing,
            suggestions=suggestions,
        )
