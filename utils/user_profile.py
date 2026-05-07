"""
User profile collection, validation, and persistence.

The profile is saved to ``~/.auto-agent-profile.json`` (or the path set in
``USER_PROFILE_PATH`` env var) so the applicant is only prompted once.

Re-run with ``--setup`` on the CLI to update stored answers.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
from pathlib import Path
from typing import Any

from models import UserProfile
from utils.logger import get_logger

log = get_logger(__name__)

_DEFAULT_PROFILE_PATH = Path.home() / ".auto-agent-profile.json"


def _profile_path() -> Path:
    """Return the path used to persist the user profile."""
    env = os.getenv("USER_PROFILE_PATH", "")
    return Path(env) if env else _DEFAULT_PROFILE_PATH


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_profile() -> UserProfile | None:
    """
    Load a previously saved :class:`~models.UserProfile` from disk.

    Returns ``None`` when no profile file is found or the file is corrupt.
    """
    path = _profile_path()
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
        profile = UserProfile(**{k: v for k, v in data.items()
                                  if k in {f.name for f in dataclasses.fields(UserProfile)}})
        log.info("Loaded existing profile from %s", path)
        return profile
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load profile from %s: %s – will re-prompt.", path, exc)
        return None


def save_profile(profile: UserProfile) -> None:
    """Persist *profile* to disk as JSON."""
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(profile), fh, indent=2)
    log.info("Profile saved to %s", path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_profile(profile: UserProfile) -> list[str]:
    """
    Check that required fields are present and well-formed.

    Returns a list of human-readable error strings (empty list → valid).
    """
    errors: list[str] = []
    if not profile.full_name.strip():
        errors.append("full_name is required.")
    if not profile.email.strip():
        errors.append("email is required.")
    elif not re.match(r"^[\w.+\-]+@([\w\-]+\.)+[a-zA-Z]{2,}$", profile.email):
        errors.append(f"email '{profile.email}' does not look valid.")
    if profile.linkedin_url and not profile.linkedin_url.startswith("http"):
        # Normalise bare linkedin.com/in/… to https://…
        profile.linkedin_url = "https://" + profile.linkedin_url
    return errors


# ---------------------------------------------------------------------------
# Interactive collection
# ---------------------------------------------------------------------------

def _prompt(label: str, default: str = "", required: bool = False) -> str:
    """Print a prompt and return the user's trimmed input (or *default*)."""
    suffix = " [required]" if required else f" [{default}]" if default else ""
    while True:
        value = input(f"  {label}{suffix}: ").strip()
        if not value and default:
            return default
        if not value and required:
            print(f"  ⚠  '{label}' is required – please enter a value.")
            continue
        return value


def _prompt_bool(label: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    raw = input(f"  {label} [{default_str}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "1", "true")


def _prompt_list(label: str, default: list[str] | None = None) -> list[str]:
    default_str = ", ".join(default) if default else ""
    raw = _prompt(label + " (comma-separated)", default=default_str)
    return [item.strip() for item in raw.split(",") if item.strip()]


def collect_profile(existing: UserProfile | None = None) -> UserProfile:
    """
    Interactively collect applicant details from stdin.

    Pre-fills each prompt with values from *existing* when provided so the
    user can confirm or update individual fields.

    Parameters
    ----------
    existing : Previously saved profile (used as defaults).

    Returns
    -------
    A validated :class:`~models.UserProfile`.
    """
    e = existing or UserProfile()

    print("\n" + "=" * 60)
    print("  AUTO-AGENT – Applicant Profile Setup")
    print("  (Press Enter to keep the existing/default value.)")
    print("=" * 60 + "\n")

    profile = UserProfile(
        full_name=_prompt("Full name", default=e.full_name, required=True),
        email=_prompt("Email address", default=e.email, required=True),
        phone=_prompt("Phone number", default=e.phone),
        linkedin_url=_prompt(
            "LinkedIn URL (e.g. linkedin.com/in/yourname)", default=e.linkedin_url
        ),
        github_url=_prompt("GitHub URL (optional)", default=e.github_url),
        portfolio_url=_prompt("Portfolio / personal website URL (optional)", default=e.portfolio_url),
        work_authorization=_prompt(
            "Work authorisation (e.g. US Citizen, Requires visa sponsorship)",
            default=e.work_authorization,
        ),
        location_preference=_prompt(
            "Location preference (Remote / On-site / Hybrid)",
            default=e.location_preference or "Hybrid",
        ),
        notice_period=_prompt(
            "Notice period (e.g. Immediate, 2 weeks, 1 month)",
            default=e.notice_period or "Immediate",
        ),
        willing_to_relocate=_prompt_bool(
            "Willing to relocate?", default=e.willing_to_relocate
        ),
        target_roles=_prompt_list(
            "Target roles / titles",
            default=e.target_roles or ["Research Intern"],
        ),
        preferred_countries=_prompt_list(
            "Preferred countries",
            default=e.preferred_countries or ["USA", "Germany", "Canada"],
        ),
        additional_notes=_prompt("Additional notes for cover letters (optional)",
                                  default=e.additional_notes),
    )

    errors = validate_profile(profile)
    if errors:
        print("\n⚠  Validation errors:")
        for err in errors:
            print(f"   • {err}")
        print("Please re-enter the highlighted fields.\n")
        return collect_profile(existing=profile)

    save_profile(profile)
    print("\n✓ Profile saved.\n")
    return profile


def get_or_collect_profile(force_setup: bool = False) -> UserProfile:
    """
    Return a valid :class:`~models.UserProfile`, loading from disk or
    prompting the user as necessary.

    Parameters
    ----------
    force_setup : When ``True``, always re-prompt even if a saved profile exists.
    """
    if not force_setup:
        profile = load_profile()
        if profile is not None:
            errors = validate_profile(profile)
            if not errors:
                return profile
            log.warning("Saved profile has validation errors – re-prompting.")
    return collect_profile(existing=load_profile())
