"""
InternshipSearchAgent
=====================
Role    : Discover research internship opportunities abroad that match the
          applicant's profile.
Input   : List of target countries, research keywords/areas (from ResumeData).
Output  : List[InternshipOpportunity]
Decision: Combines keyword matching against a curated set of sources;
          falls back to synthetic (LLM-generated) listings when live scraping
          is unavailable (no network / blocked domain).

Note: Production deployments should plug in real job-board API clients
      (LinkedIn, Indeed, DAAD, Research Internships, etc.) here.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from config import DEFAULT_COUNTRIES, MAX_JOBS_PER_COUNTRY
from models import InternshipOpportunity, ResumeData
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Representative internship data used when live search is disabled.
# A real implementation replaces this with API / web-scraping calls.
# ---------------------------------------------------------------------------
_SAMPLE_INTERNSHIPS: list[dict] = [
    {
        "title": "Research Intern – Machine Learning",
        "organization": "Max Planck Institute for Intelligent Systems",
        "country": "Germany",
        "city": "Tübingen",
        "description": (
            "Join our group to work on deep generative models, transformers, "
            "and reinforcement learning. Strong Python and PyTorch skills required."
        ),
        "required_skills": ["Python", "PyTorch", "deep learning"],
        "preferred_skills": ["transformer", "NLP", "reinforcement learning"],
        "application_url": "https://is.mpg.de/careers",
        "deadline": "2026-03-31",
        "duration": "3–6 months",
        "stipend": "€1,500/month",
        "research_area": "Machine Learning",
        "source": "sample",
    },
    {
        "title": "AI/ML Research Internship",
        "organization": "Vector Institute",
        "country": "Canada",
        "city": "Toronto",
        "description": (
            "Work alongside leading researchers on NLP, computer vision, and "
            "trustworthy AI. Experience with TensorFlow or PyTorch required."
        ),
        "required_skills": ["Python", "TensorFlow", "machine learning"],
        "preferred_skills": ["NLP", "computer vision", "fairness in AI"],
        "application_url": "https://vectorinstitute.ai/careers",
        "deadline": "2026-04-15",
        "duration": "4 months",
        "stipend": "CAD 2,000/month",
        "research_area": "AI / NLP",
        "source": "sample",
    },
    {
        "title": "Research Intern – Computational Biology",
        "organization": "Broad Institute of MIT and Harvard",
        "country": "USA",
        "city": "Cambridge, MA",
        "description": (
            "Apply machine learning to genomics and drug discovery. "
            "Python, bioinformatics pipelines, and statistical modelling expected."
        ),
        "required_skills": ["Python", "bioinformatics", "statistics"],
        "preferred_skills": ["deep learning", "PyTorch", "genomics"],
        "application_url": "https://www.broadinstitute.org/careers",
        "deadline": "2026-02-28",
        "duration": "3 months",
        "stipend": "USD 4,000/month",
        "research_area": "Computational Biology",
        "source": "sample",
    },
    {
        "title": "NLP Research Intern",
        "organization": "INRIA",
        "country": "France",
        "city": "Paris",
        "description": (
            "Research on large language models, dialogue systems, and multilingual "
            "NLP. French language skill is a plus but not required."
        ),
        "required_skills": ["Python", "NLP", "deep learning"],
        "preferred_skills": ["French", "transformer", "text generation"],
        "application_url": "https://www.inria.fr/en/jobs",
        "deadline": "2026-03-15",
        "duration": "6 months",
        "stipend": "€1,800/month",
        "research_area": "NLP",
        "source": "sample",
    },
    {
        "title": "HCI Research Internship",
        "organization": "ETH Zürich",
        "country": "Switzerland",
        "city": "Zürich",
        "description": (
            "Explore human-computer interaction in immersive environments. "
            "Experience in user studies and prototyping desirable."
        ),
        "required_skills": ["HCI", "user research", "prototyping"],
        "preferred_skills": ["AR/VR", "Python", "Unity"],
        "application_url": "https://hci.ethz.ch",
        "deadline": "2026-05-01",
        "duration": "3–4 months",
        "stipend": "CHF 2,500/month",
        "research_area": "HCI",
        "source": "sample",
    },
    {
        "title": "Robotics Research Intern",
        "organization": "Delft University of Technology",
        "country": "Netherlands",
        "city": "Delft",
        "description": (
            "Research on autonomous drone navigation and simultaneous localisation "
            "and mapping (SLAM). ROS and C++ proficiency expected."
        ),
        "required_skills": ["ROS", "C++", "robotics"],
        "preferred_skills": ["Python", "SLAM", "computer vision"],
        "application_url": "https://www.tudelft.nl/en/about-tu-delft/working-at-tu-delft",
        "deadline": "2026-04-30",
        "duration": "4–6 months",
        "stipend": "€1,200/month",
        "research_area": "Robotics",
        "source": "sample",
    },
]


class InternshipSearchAgent:
    """
    Searches for research internship opportunities.

    In production, swap :meth:`_live_search` bodies with real API/scraping calls.
    The :meth:`_sample_search` method provides offline fallback data.
    """

    def __init__(self, llm: LLMClient | None = None, use_sample_data: bool = True) -> None:
        self._llm = llm or LLMClient()
        self._use_sample = use_sample_data

    # ------------------------------------------------------------------
    def search(
        self,
        resume: ResumeData,
        countries: Sequence[str] | None = None,
        max_per_country: int = MAX_JOBS_PER_COUNTRY,
    ) -> list[InternshipOpportunity]:
        """
        Return a list of matching internship opportunities.

        Parameters
        ----------
        resume          : Parsed applicant profile used for relevance filtering.
        countries       : Target countries; defaults to :data:`config.DEFAULT_COUNTRIES`.
        max_per_country : Cap on results per country.
        """
        target_countries = [c.strip() for c in (countries or DEFAULT_COUNTRIES)]
        log.info(
            "[bold]InternshipSearchAgent[/] – searching %d countries…",
            len(target_countries),
        )

        source = self._sample_search if self._use_sample else self._live_search
        raw_results = source(resume, target_countries)

        filtered = self._filter_by_relevance(raw_results, resume, max_per_country)
        log.info("Found %d relevant opportunities.", len(filtered))
        return filtered

    # ------------------------------------------------------------------ sources
    def _sample_search(
        self, resume: ResumeData, countries: list[str]
    ) -> list[InternshipOpportunity]:
        """Return sample data filtered to the requested countries."""
        country_set = {c.lower() for c in countries}
        results = []
        for item in _SAMPLE_INTERNSHIPS:
            if item["country"].lower() in country_set:
                results.append(self._dict_to_opportunity(item))
        return results

    def _live_search(
        self, resume: ResumeData, countries: list[str]
    ) -> list[InternshipOpportunity]:  # pragma: no cover
        """
        Placeholder for live job-board API calls.

        Extend this method to integrate with:
        - LinkedIn Jobs API
        - Indeed Publisher API
        - DAAD Scholarship Database
        - Research Internships (researchinternships.net)
        - Handshake API
        """
        log.warning("Live search not implemented – falling back to sample data.")
        return self._sample_search(resume, countries)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _dict_to_opportunity(data: dict) -> InternshipOpportunity:
        return InternshipOpportunity(
            job_id=str(uuid.uuid4()),
            title=data.get("title", ""),
            organization=data.get("organization", ""),
            country=data.get("country", ""),
            city=data.get("city", ""),
            description=data.get("description", ""),
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            application_url=data.get("application_url", ""),
            deadline=data.get("deadline", ""),
            duration=data.get("duration", ""),
            stipend=data.get("stipend", ""),
            research_area=data.get("research_area", ""),
            source=data.get("source", ""),
        )

    @staticmethod
    def _filter_by_relevance(
        opportunities: list[InternshipOpportunity],
        resume: ResumeData,
        max_per_country: int,
    ) -> list[InternshipOpportunity]:
        """
        Score each opportunity by keyword overlap with the applicant's skills
        and keep at most *max_per_country* per country.
        """
        applicant_skills = {s.lower() for s in resume.skills}
        country_counts: dict[str, int] = {}
        scored: list[tuple[int, InternshipOpportunity]] = []

        for opp in opportunities:
            required = {s.lower() for s in opp.required_skills}
            preferred = {s.lower() for s in opp.preferred_skills}
            score = len(applicant_skills & required) * 2 + len(applicant_skills & preferred)
            scored.append((score, opp))

        # Sort descending by relevance score then alphabetically by title
        scored.sort(key=lambda t: (-t[0], t[1].title))

        results = []
        for _, opp in scored:
            count = country_counts.get(opp.country, 0)
            if count < max_per_country:
                results.append(opp)
                country_counts[opp.country] = count + 1

        return results
