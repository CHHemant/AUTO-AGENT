"""Tests for ResumeParserAgent."""

import json
import pytest

from agents.resume_parser import ResumeParserAgent
from models import ResumeData
from utils.llm_client import LLMClient


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_parser(llm: LLMClient) -> ResumeParserAgent:
    return ResumeParserAgent(llm=llm)


# ─── tests ───────────────────────────────────────────────────────────────────

class TestResumeParserAgent:
    def test_parse_returns_resume_data(self, mock_llm: LLMClient) -> None:
        parser = _make_parser(mock_llm)
        result = parser.parse("Jane Doe\njane.doe@example.com\nSkills: Python")
        assert isinstance(result, ResumeData)

    def test_parse_extracts_name(self, mock_llm: LLMClient) -> None:
        parser = _make_parser(mock_llm)
        result = parser.parse("Jane Doe\njane.doe@example.com")
        assert result.full_name == "Jane Doe"

    def test_parse_extracts_email(self, mock_llm: LLMClient) -> None:
        parser = _make_parser(mock_llm)
        result = parser.parse("Jane Doe\njane.doe@example.com")
        assert result.email == "jane.doe@example.com"

    def test_parse_extracts_skills(self, mock_llm: LLMClient) -> None:
        parser = _make_parser(mock_llm)
        result = parser.parse("Jane Doe\nSkills: Python, PyTorch")
        assert "Python" in result.skills

    def test_raw_text_preserved(self, mock_llm: LLMClient) -> None:
        raw = "Jane Doe\njane@example.com\nSkills: Python"
        parser = _make_parser(mock_llm)
        result = parser.parse(raw)
        assert result.raw_text == raw

    def test_parse_json_valid(self) -> None:
        data = {"full_name": "Bob", "email": "bob@x.com", "skills": ["Go", "Rust"]}
        result = ResumeParserAgent._parse_json(json.dumps(data))
        assert result is not None
        assert result["full_name"] == "Bob"

    def test_parse_json_with_fences(self) -> None:
        data = json.dumps({"full_name": "Bob"})
        fenced = f"```json\n{data}\n```"
        result = ResumeParserAgent._parse_json(fenced)
        assert result is not None
        assert result["full_name"] == "Bob"

    def test_parse_json_invalid_returns_none(self) -> None:
        result = ResumeParserAgent._parse_json("not json at all")
        assert result is None

    def test_regex_fallback_extracts_email(self) -> None:
        text = "John Smith\njohn.smith@university.edu\nSkills: Python, ML"
        result = ResumeParserAgent._regex_fallback(text)
        assert result["email"] == "john.smith@university.edu"

    def test_regex_fallback_extracts_name(self) -> None:
        text = "John Smith\njohn@example.com"
        result = ResumeParserAgent._regex_fallback(text)
        assert result["full_name"] == "John Smith"

    def test_regex_fallback_extracts_skills(self) -> None:
        text = "John\nSkills: Python, Machine Learning, TensorFlow"
        result = ResumeParserAgent._regex_fallback(text)
        assert any("Python" in s for s in result["skills"])
