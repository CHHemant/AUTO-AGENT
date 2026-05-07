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

  # Enable live submission (use with caution)
  python main.py --resume path/to/resume.pdf --no-dry-run
"""

from __future__ import annotations

import argparse
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.flowchart:
        from flowchart import print_flowchart  # noqa: PLC0415
        print_flowchart()
        return 0

    if not args.resume:
        console.print(
            "[bold red]Error:[/] --resume is required. "
            "Run with --flowchart to see the system architecture.",
            highlight=False,
        )
        return 1

    from agents.orchestrator import OrchestratorAgent  # noqa: PLC0415

    orchestrator = OrchestratorAgent(dry_run=not args.live)
    records = orchestrator.run(
        resume_path=args.resume,
        countries=args.countries,
    )

    return 0 if any(r.status.value == "submitted" for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
