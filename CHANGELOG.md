# Changelog

All notable changes to AUTO-AGENT are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] – 2026-05-07

### Highlights

- **Multi-provider LLM support**: run the pipeline with OpenAI, Anthropic Claude,
  or Google Gemini — chosen by a single environment variable or `--provider` CLI flag.
- **Applicant profile onboarding**: a guided setup wizard collects LinkedIn URL,
  work authorisation, location preference, and other job-application details once
  and reuses them across every application.
- **38 new tests** (87 total) covering provider routing, mock fallback, and
  profile validation / persistence.

### Added

#### Multi-provider LLM layer (`utils/llm_client.py`)
- `LLM_PROVIDER` env var selects the active backend: `openai` (default),
  `anthropic`, or `google`.
- Per-provider default models: `gpt-4o`, `claude-opus-4-5`, `gemini-1.5-pro`.
  Override any with `LLM_MODEL=<model-name>`.
- `LLMClient._call_anthropic()` – Anthropic Messages API integration.
- `LLMClient._call_google()` – Google Generative AI (Gemini) integration.
- Mock mode remains active when the chosen provider's key is absent; no API
  credits are consumed during testing.
- Clear `ValueError` when `LLM_PROVIDER` is set to an unknown value.

#### New config keys (`config.py`)
- `LLM_PROVIDER` – provider selector.
- `ANTHROPIC_API_KEY` – key for the Anthropic backend.
- `GOOGLE_API_KEY` – key for the Google Gemini backend.
- `_DEFAULT_MODELS` – per-provider sensible defaults (internal constant).

#### Applicant profile (`utils/user_profile.py`, `models.UserProfile`)
- `UserProfile` dataclass: `full_name`, `email`, `phone`, `linkedin_url`,
  `github_url`, `portfolio_url`, `work_authorization`, `location_preference`,
  `notice_period`, `willing_to_relocate`, `target_roles`, `preferred_countries`,
  `additional_notes`.
- `collect_profile()` – interactive stdin wizard with defaults and validation.
- `validate_profile()` – checks required fields and email format; normalises
  bare LinkedIn URLs to `https://…`.
- `save_profile()` / `load_profile()` – JSON persistence at
  `~/.auto-agent-profile.json` (path overridable via `USER_PROFILE_PATH`).
- `get_or_collect_profile(force_setup)` – loads saved profile or prompts if
  absent / invalid.

#### CLI (`main.py`)
- `--provider {openai,anthropic,google}` – overrides `LLM_PROVIDER` at runtime.
- `--setup` – runs the profile wizard and exits (no resume required).
- Profile is loaded / collected automatically before pipeline start.

#### Profile injection (`agents/cover_letter.py`, `agents/orchestrator.py`)
- `CoverLetterAgent.generate()` accepts an optional `UserProfile`; when present,
  LinkedIn URL, GitHub, portfolio, work authorisation, location preference,
  notice period, and additional notes are included in the cover-letter prompt.
- `OrchestratorAgent.__init__()` accepts an optional `profile` parameter and
  threads it through to `CoverLetterAgent`.

#### New dependencies (`requirements.txt`)
- `anthropic>=0.40.0`
- `google-generativeai>=0.8.3`

#### New tests
- `tests/test_llm_client.py` (15 tests) – mock mode per provider, provider
  detection, canned responses, invalid-provider error.
- `tests/test_user_profile.py` (23 tests) – validation edge cases, save/load
  round-trip, interactive collection with mocked stdin, force-setup flag.
- `tests/conftest.py` – `sample_profile` fixture; `mock_llm` now clears all
  three provider keys.

#### Documentation
- `README.md` – provider comparison table, free-tier guidance, `--setup` and
  `--provider` quick-start examples, updated project-structure tree.
- `CHANGELOG.md` – this file.

### Changed

- `LLMClient` now imports `config` as a module (not `from config import …`)
  so test fixtures can patch individual config attributes reliably.
- `OrchestratorAgent.__init__()` signature: new optional `profile` kwarg
  (backward-compatible; defaults to `None`).
- `CoverLetterAgent.generate()` signature: new optional `profile` kwarg
  (backward-compatible; defaults to `None`).

### Fixed

- Email validation regex in `validate_profile` now correctly accepts
  subdomain addresses such as `user@sub.example.co.uk`.

---

## [1.0.0] – initial release

- Seven-agent pipeline: resume parser → internship search → resume tailor →
  ATS scorer → feedback loop → cover letter → application submitter.
- OpenAI ChatCompletion backend with mock fallback.
- 49 tests covering all core agents.
