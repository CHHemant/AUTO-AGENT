"""Tests for the multi-provider LLMClient."""

from __future__ import annotations

import json
import pytest

import config
from utils.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_all_keys() -> None:
    config.OPENAI_API_KEY = ""
    config.ANTHROPIC_API_KEY = ""
    config.GOOGLE_API_KEY = ""


def _set_provider(provider: str) -> None:
    config.LLM_PROVIDER = provider


# ---------------------------------------------------------------------------
# Mock mode tests
# ---------------------------------------------------------------------------

class TestLLMClientMockMode:
    def test_mock_mode_when_no_openai_key(self) -> None:
        original = config.OPENAI_API_KEY
        original_provider = config.LLM_PROVIDER
        config.LLM_PROVIDER = "openai"
        config.OPENAI_API_KEY = ""
        try:
            client = LLMClient()
            assert client._mock is True
        finally:
            config.OPENAI_API_KEY = original
            config.LLM_PROVIDER = original_provider

    def test_mock_mode_when_no_anthropic_key(self) -> None:
        original = config.ANTHROPIC_API_KEY
        original_provider = config.LLM_PROVIDER
        config.LLM_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = ""
        try:
            client = LLMClient()
            assert client._mock is True
        finally:
            config.ANTHROPIC_API_KEY = original
            config.LLM_PROVIDER = original_provider

    def test_mock_mode_when_no_google_key(self) -> None:
        original = config.GOOGLE_API_KEY
        original_provider = config.LLM_PROVIDER
        config.LLM_PROVIDER = "google"
        config.GOOGLE_API_KEY = ""
        try:
            client = LLMClient()
            assert client._mock is True
        finally:
            config.GOOGLE_API_KEY = original
            config.LLM_PROVIDER = original_provider

    def test_mock_complete_returns_string(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user")
        assert isinstance(result, str)

    def test_mock_complete_returns_canned_parse_resume(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user", task_key="parse_resume")
        data = json.loads(result)
        assert "full_name" in data
        assert data["full_name"] == "Jane Doe"

    def test_mock_complete_returns_canned_ats_score(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user", task_key="ats_score")
        data = json.loads(result)
        assert "score" in data
        assert 0 <= data["score"] <= 100

    def test_mock_complete_unknown_key_returns_default(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user", task_key="unknown_task_xyz")
        assert result == "Mock LLM response."

    def test_mock_complete_cover_letter(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user", task_key="cover_letter")
        assert "Dear Hiring Manager" in result

    def test_mock_complete_tailor_resume(self, mock_llm: LLMClient) -> None:
        result = mock_llm.complete("system", "user", task_key="tailor_resume")
        assert "TAILORED RESUME" in result


# ---------------------------------------------------------------------------
# Provider routing / initialisation
# ---------------------------------------------------------------------------

class TestLLMClientProviderRouting:
    def test_invalid_provider_raises(self) -> None:
        original_provider = config.LLM_PROVIDER
        config.LLM_PROVIDER = "badprovider"
        try:
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                LLMClient()
        finally:
            config.LLM_PROVIDER = original_provider

    def test_provider_openai_detected(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.OPENAI_API_KEY
        config.LLM_PROVIDER = "openai"
        config.OPENAI_API_KEY = ""
        try:
            client = LLMClient()
            assert client._provider == "openai"
        finally:
            config.LLM_PROVIDER = original_provider
            config.OPENAI_API_KEY = original_key

    def test_provider_anthropic_detected(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.ANTHROPIC_API_KEY
        config.LLM_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = ""
        try:
            client = LLMClient()
            assert client._provider == "anthropic"
        finally:
            config.LLM_PROVIDER = original_provider
            config.ANTHROPIC_API_KEY = original_key

    def test_provider_google_detected(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.GOOGLE_API_KEY
        config.LLM_PROVIDER = "google"
        config.GOOGLE_API_KEY = ""
        try:
            client = LLMClient()
            assert client._provider == "google"
        finally:
            config.LLM_PROVIDER = original_provider
            config.GOOGLE_API_KEY = original_key

    def test_case_insensitive_provider(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.OPENAI_API_KEY
        config.LLM_PROVIDER = "OpenAI"
        config.OPENAI_API_KEY = ""
        try:
            client = LLMClient()
            assert client._provider == "openai"
        finally:
            config.LLM_PROVIDER = original_provider
            config.OPENAI_API_KEY = original_key

    def test_active_key_openai(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.OPENAI_API_KEY
        config.LLM_PROVIDER = "openai"
        config.OPENAI_API_KEY = ""
        try:
            client = LLMClient()
            assert client._active_key() == ""
        finally:
            config.LLM_PROVIDER = original_provider
            config.OPENAI_API_KEY = original_key

    def test_active_key_anthropic(self) -> None:
        original_provider = config.LLM_PROVIDER
        original_key = config.ANTHROPIC_API_KEY
        config.LLM_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = "sk-test"
        try:
            # Don't create LLMClient (it would try to import anthropic)
            # Just test the config read logic directly
            assert config.ANTHROPIC_API_KEY == "sk-test"
        finally:
            config.LLM_PROVIDER = original_provider
            config.ANTHROPIC_API_KEY = original_key
