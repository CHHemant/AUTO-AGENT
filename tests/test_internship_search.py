"""Tests for InternshipSearchAgent."""

import pytest

from agents.internship_search import InternshipSearchAgent
from models import InternshipOpportunity, ResumeData
from utils.llm_client import LLMClient


class TestInternshipSearchAgent:
    def test_search_returns_list(
        self, mock_llm: LLMClient, sample_resume: ResumeData
    ) -> None:
        agent = InternshipSearchAgent(llm=mock_llm, use_sample_data=True)
        results = agent.search(sample_resume, countries=["Germany"])
        assert isinstance(results, list)

    def test_search_filters_by_country(
        self, mock_llm: LLMClient, sample_resume: ResumeData
    ) -> None:
        agent = InternshipSearchAgent(llm=mock_llm, use_sample_data=True)
        results = agent.search(sample_resume, countries=["Germany"])
        for opp in results:
            assert opp.country == "Germany"

    def test_search_respects_max_per_country(
        self, mock_llm: LLMClient, sample_resume: ResumeData
    ) -> None:
        agent = InternshipSearchAgent(llm=mock_llm, use_sample_data=True)
        results = agent.search(sample_resume, countries=["Germany", "Canada", "USA"], max_per_country=1)
        country_counts: dict[str, int] = {}
        for opp in results:
            country_counts[opp.country] = country_counts.get(opp.country, 0) + 1
        for count in country_counts.values():
            assert count <= 1

    def test_search_opportunity_has_required_fields(
        self, mock_llm: LLMClient, sample_resume: ResumeData
    ) -> None:
        agent = InternshipSearchAgent(llm=mock_llm, use_sample_data=True)
        results = agent.search(sample_resume, countries=["Germany"])
        for opp in results:
            assert isinstance(opp, InternshipOpportunity)
            assert opp.job_id  # should have a UUID
            assert opp.title
            assert opp.organization

    def test_filter_by_relevance_sorts_by_skill_overlap(self) -> None:
        resume = ResumeData(skills=["Python", "PyTorch", "NLP"])
        opps = [
            InternshipOpportunity(
                job_id="a", title="A", country="USA",
                required_skills=["Python", "PyTorch"],
                preferred_skills=["NLP"],
            ),
            InternshipOpportunity(
                job_id="b", title="B", country="USA",
                required_skills=["Java"],
                preferred_skills=[],
            ),
        ]
        results = InternshipSearchAgent._filter_by_relevance(opps, resume, max_per_country=10)
        # The one with more overlapping skills should come first
        assert results[0].job_id == "a"

    def test_empty_countries_returns_empty(
        self, mock_llm: LLMClient, sample_resume: ResumeData
    ) -> None:
        agent = InternshipSearchAgent(llm=mock_llm, use_sample_data=True)
        results = agent.search(sample_resume, countries=["Narnia"])
        assert results == []
