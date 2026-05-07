"""Tests for utils.user_profile – load/save/validate/collect."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from models import UserProfile
from utils.user_profile import (
    collect_profile,
    get_or_collect_profile,
    load_profile,
    save_profile,
    validate_profile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_profile_path(tmp_path: Path) -> Path:
    """Override USER_PROFILE_PATH to a temp file for isolation."""
    p = tmp_path / "test_profile.json"
    os.environ["USER_PROFILE_PATH"] = str(p)
    yield p
    os.environ.pop("USER_PROFILE_PATH", None)


@pytest.fixture()
def valid_profile() -> UserProfile:
    return UserProfile(
        full_name="Bob Tester",
        email="bob@example.com",
        phone="+1-555-0200",
        linkedin_url="https://linkedin.com/in/bobtester",
        github_url="https://github.com/bobtester",
        work_authorization="EU Citizen",
        location_preference="Remote",
        notice_period="Immediate",
        willing_to_relocate=True,
        target_roles=["Research Intern"],
        preferred_countries=["Germany"],
    )


# ---------------------------------------------------------------------------
# validate_profile
# ---------------------------------------------------------------------------

class TestValidateProfile:
    def test_valid_profile_returns_no_errors(self, valid_profile: UserProfile) -> None:
        errors = validate_profile(valid_profile)
        assert errors == []

    def test_missing_full_name(self, valid_profile: UserProfile) -> None:
        valid_profile.full_name = ""
        errors = validate_profile(valid_profile)
        assert any("full_name" in e for e in errors)

    def test_missing_email(self, valid_profile: UserProfile) -> None:
        valid_profile.email = ""
        errors = validate_profile(valid_profile)
        assert any("email" in e for e in errors)

    def test_invalid_email_format(self, valid_profile: UserProfile) -> None:
        valid_profile.email = "not-an-email"
        errors = validate_profile(valid_profile)
        assert any("email" in e for e in errors)

    def test_valid_email_accepted(self, valid_profile: UserProfile) -> None:
        valid_profile.email = "user+tag@sub.example.co.uk"
        errors = validate_profile(valid_profile)
        assert errors == []

    def test_bare_linkedin_url_normalised(self, valid_profile: UserProfile) -> None:
        valid_profile.linkedin_url = "linkedin.com/in/bob"
        validate_profile(valid_profile)
        assert valid_profile.linkedin_url.startswith("https://")

    def test_https_linkedin_url_unchanged(self, valid_profile: UserProfile) -> None:
        valid_profile.linkedin_url = "https://linkedin.com/in/bob"
        validate_profile(valid_profile)
        assert valid_profile.linkedin_url == "https://linkedin.com/in/bob"

    def test_empty_linkedin_url_no_error(self, valid_profile: UserProfile) -> None:
        valid_profile.linkedin_url = ""
        errors = validate_profile(valid_profile)
        assert errors == []

    def test_multiple_errors_reported(self) -> None:
        profile = UserProfile(full_name="", email="bad")
        errors = validate_profile(profile)
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# save_profile / load_profile
# ---------------------------------------------------------------------------

class TestSaveLoadProfile:
    def test_save_creates_file(self, valid_profile: UserProfile, tmp_profile_path: Path) -> None:
        save_profile(valid_profile)
        assert tmp_profile_path.exists()

    def test_save_writes_valid_json(self, valid_profile: UserProfile, tmp_profile_path: Path) -> None:
        save_profile(valid_profile)
        data = json.loads(tmp_profile_path.read_text(encoding="utf-8"))
        assert data["full_name"] == valid_profile.full_name
        assert data["email"] == valid_profile.email

    def test_load_returns_none_when_no_file(self, tmp_profile_path: Path) -> None:
        result = load_profile()
        assert result is None

    def test_load_returns_profile_when_file_exists(
        self, valid_profile: UserProfile, tmp_profile_path: Path
    ) -> None:
        save_profile(valid_profile)
        loaded = load_profile()
        assert loaded is not None
        assert loaded.full_name == valid_profile.full_name
        assert loaded.email == valid_profile.email

    def test_load_returns_none_on_corrupt_file(self, tmp_profile_path: Path) -> None:
        tmp_profile_path.write_text("{ this is not json }", encoding="utf-8")
        result = load_profile()
        assert result is None

    def test_roundtrip_all_fields(self, valid_profile: UserProfile, tmp_profile_path: Path) -> None:
        save_profile(valid_profile)
        loaded = load_profile()
        assert loaded is not None
        assert dataclasses.asdict(loaded) == dataclasses.asdict(valid_profile)

    def test_load_ignores_unknown_json_keys(self, tmp_profile_path: Path) -> None:
        data = {"full_name": "Alice", "email": "alice@example.com", "unknown_key": "value"}
        tmp_profile_path.write_text(json.dumps(data), encoding="utf-8")
        loaded = load_profile()
        assert loaded is not None
        assert loaded.full_name == "Alice"


# ---------------------------------------------------------------------------
# collect_profile (interactive)
# ---------------------------------------------------------------------------

class TestCollectProfile:
    def test_collect_with_all_inputs(self, tmp_profile_path: Path) -> None:
        inputs = [
            "Carol Test",       # full_name
            "carol@test.com",   # email
            "+1-555-0303",      # phone
            "linkedin.com/in/carol",  # linkedin_url
            "",                 # github_url (skip)
            "",                 # portfolio_url (skip)
            "US Citizen",       # work_authorization
            "Remote",           # location_preference
            "2 weeks",          # notice_period
            "y",                # willing_to_relocate
            "Research Intern",  # target_roles
            "USA",              # preferred_countries
            "",                 # additional_notes (skip)
        ]
        with patch("builtins.input", side_effect=inputs):
            profile = collect_profile()
        assert profile.full_name == "Carol Test"
        assert profile.email == "carol@test.com"
        assert profile.phone == "+1-555-0303"
        assert "https://" in profile.linkedin_url
        assert profile.work_authorization == "US Citizen"
        assert profile.location_preference == "Remote"
        assert profile.notice_period == "2 weeks"
        assert profile.willing_to_relocate is True

    def test_collect_saves_to_disk(self, tmp_profile_path: Path) -> None:
        inputs = [
            "Dave Save", "dave@save.com", "", "", "", "",
            "", "Hybrid", "Immediate", "y", "Intern", "Germany", "",
        ]
        with patch("builtins.input", side_effect=inputs):
            collect_profile()
        assert tmp_profile_path.exists()

    def test_collect_invalid_email_reprompts(self, tmp_profile_path: Path) -> None:
        # First attempt has bad email; second attempt fixes it.
        # On re-prompt all 13 fields are shown again with existing values as defaults.
        inputs = [
            # ── first call ──────────────────────────────────────────────────
            "Eve Test",     # full_name
            "notvalid",     # email (bad)
            "",             # phone
            "",             # linkedin_url
            "",             # github_url
            "",             # portfolio_url
            "",             # work_authorization
            "Hybrid",       # location_preference
            "Immediate",    # notice_period
            "y",            # willing_to_relocate
            "Intern",       # target_roles
            "Germany",      # preferred_countries
            "",             # additional_notes
            # ── recursive re-prompt ─────────────────────────────────────────
            "Eve Test",     # full_name
            "eve@ok.com",   # email (good)
            "",             # phone
            "",             # linkedin_url
            "",             # github_url
            "",             # portfolio_url
            "",             # work_authorization
            "Hybrid",       # location_preference
            "Immediate",    # notice_period
            "y",            # willing_to_relocate
            "Intern",       # target_roles
            "Germany",      # preferred_countries
            "",             # additional_notes
        ]
        with patch("builtins.input", side_effect=inputs):
            profile = collect_profile()
        assert profile.email == "eve@ok.com"


# ---------------------------------------------------------------------------
# get_or_collect_profile
# ---------------------------------------------------------------------------

class TestGetOrCollectProfile:
    def test_returns_saved_profile_without_prompting(
        self, valid_profile: UserProfile, tmp_profile_path: Path
    ) -> None:
        save_profile(valid_profile)
        with patch("builtins.input") as mock_input:
            result = get_or_collect_profile(force_setup=False)
            mock_input.assert_not_called()
        assert result.full_name == valid_profile.full_name

    def test_force_setup_reprompts_even_with_saved_profile(
        self, valid_profile: UserProfile, tmp_profile_path: Path
    ) -> None:
        save_profile(valid_profile)
        inputs = [
            valid_profile.full_name,
            valid_profile.email,
            "", "", "", "",
            "", "Hybrid", "Immediate", "y", "Research Intern", "Germany", "",
        ]
        with patch("builtins.input", side_effect=inputs):
            result = get_or_collect_profile(force_setup=True)
        assert result.full_name == valid_profile.full_name

    def test_prompts_when_no_file_exists(self, tmp_profile_path: Path) -> None:
        inputs = [
            "Frank New", "frank@new.com", "", "", "", "",
            "", "On-site", "1 month", "n", "ML Intern", "USA", "",
        ]
        with patch("builtins.input", side_effect=inputs):
            result = get_or_collect_profile(force_setup=False)
        assert result.full_name == "Frank New"
