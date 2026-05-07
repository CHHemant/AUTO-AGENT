"""
AUTO-AGENT – Main entry point.

Usage
─────
  # Print the system flowchart
  python main.py --flowchart

  # Run the full pipeline (dry-run, no real submission)
  python main.py --resume path/to/resume.pdf

  # Run for specific countries
  python main.py --resume path/to/resume.pdf --countries USA Canada Germany

  # Choose an LLM provider (openai | anthropic | google)
  python main.py --resume path/to/resume.pdf --provider anthropic

  # (Re-)run the applicant profile setup wizard
  python main.py --setup

  # Enable live submission (use with caution)
  python main.py --resume path/to/resume.pdf --no-dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

from rich.console import Console

console = Console()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auto-agent",
        description="Automated research internship application system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--resume",
        metavar="PATH",
        help="Path to your resume file (.pdf, .docx, or .txt).",
    )
    p.add_argument(
        "--countries",
        nargs="+",
        metavar="COUNTRY",
        help="Target countries for the search (e.g. USA Germany Canada).",
    )
    p.add_argument(
        "--flowchart",
        action="store_true",
        help="Print the system architecture flowchart and exit.",
    )
    p.add_argument(
        "--no-dry-run",
        dest="live",
        action="store_true",
        default=False,
        help="Actually submit applications (default: dry-run only).",
    )
    p.add_argument(
        "--provider",
        metavar="PROVIDER",
        choices=["openai", "anthropic", "google"],
        help=(
            "LLM provider to use: openai, anthropic, or google. "
            "Overrides the LLM_PROVIDER environment variable."
        ),
    )
    p.add_argument(
        "--setup",
        action="store_true",
        help="Run the applicant profile setup wizard and exit.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Allow CLI --provider to override the env var before LLMClient is created
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        # Reload config so LLM_PROVIDER is picked up
        import importlib
        import config
        importlib.reload(config)

    if args.flowchart:
        from flowchart import print_flowchart  # noqa: PLC0415
        print_flowchart()
        return 0

    # ── Profile setup wizard ────────────────────────────────────────────────
    from utils.user_profile import get_or_collect_profile  # noqa: PLC0415

    if args.setup:
        get_or_collect_profile(force_setup=True)
        return 0

    if not args.resume:
        console.print(
            "[bold red]Error:[/] --resume is required. "
            "Run with --flowchart to see the system architecture, "
            "or --setup to configure your applicant profile.",
            highlight=False,
        )
        return 1

    # Collect / load applicant profile (non-interactive if already saved)
    profile = get_or_collect_profile(force_setup=False)

    from agents.orchestrator import OrchestratorAgent  # noqa: PLC0415

    orchestrator = OrchestratorAgent(dry_run=not args.live, profile=profile)
    records = orchestrator.run(
        resume_path=args.resume,
        countries=args.countries,
    )

    return 0 if any(r.status.value == "submitted" for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
