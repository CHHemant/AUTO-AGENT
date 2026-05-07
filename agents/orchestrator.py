"""
OrchestratorAgent
=================
Role    : Central controller that coordinates all specialised agents to
          deliver end-to-end internship applications.

Workflow (per opportunity)
──────────────────────────
  1. ResumeParserAgent   – Parse raw resume text → ResumeData
  2. InternshipSearchAgent – Search for opportunities → List[InternshipOpportunity]
  3. For each opportunity:
     a. ResumeTailoringAgent  – Tailor resume to the role
     b. ATSScorerAgent        – Score tailored resume
     c. FeedbackLoopAgent     – ACCEPT / REFINE / SKIP decision
        • If REFINE → go to step 3a (up to ATS_MAX_RETRIES times)
        • If SKIP   → mark record as SKIPPED, move to next opportunity
        • If ACCEPT → continue to step 3d
     d. CoverLetterAgent      – Write cover letter
     e. ApplicationSubmitter  – Submit application

Inputs  : resume_path (str), target_countries (list[str] | None),
          dry_run (bool) – when True, skip actual submission
Outputs : List[ApplicationRecord] – full audit trail for every application
"""

from __future__ import annotations

from typing import Sequence

from agents.ats_scorer import ATSScorerAgent
from agents.application_submitter import ApplicationSubmitterAgent
from agents.cover_letter import CoverLetterAgent
from agents.feedback_loop import FeedbackDecision, FeedbackLoopAgent
from agents.internship_search import InternshipSearchAgent
from agents.resume_parser import ResumeParserAgent
from agents.resume_tailor import ResumeTailoringAgent
from models import ApplicationRecord, ApplicationStatus, UserProfile
from utils.file_handler import FileHandler
from utils.llm_client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)


class OrchestratorAgent:
    """
    Top-level coordinator for the AUTO-AGENT pipeline.

    All individual agents are injected via the constructor to allow easy
    unit-testing and mock substitution.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        use_sample_data: bool = True,
        dry_run: bool = True,
        profile: UserProfile | None = None,
    ) -> None:
        _llm = llm or LLMClient()
        self._parser     = ResumeParserAgent(llm=_llm)
        self._searcher   = InternshipSearchAgent(llm=_llm, use_sample_data=use_sample_data)
        self._tailor     = ResumeTailoringAgent(llm=_llm)
        self._ats        = ATSScorerAgent(llm=_llm)
        self._cover      = CoverLetterAgent(llm=_llm)
        self._submitter  = ApplicationSubmitterAgent()
        self._feedback   = FeedbackLoopAgent()
        self._fh         = FileHandler()
        self._dry_run    = dry_run
        self._profile    = profile

    # ------------------------------------------------------------------
    def run(
        self,
        resume_path: str,
        countries: Sequence[str] | None = None,
    ) -> list[ApplicationRecord]:
        """
        Execute the full pipeline for a given resume file.

        Parameters
        ----------
        resume_path : Absolute or relative path to the applicant's resume
                      (.pdf / .docx / .txt).
        countries   : Target countries; if None, uses DEFAULT_COUNTRIES from
                      config.

        Returns
        -------
        List of :class:`ApplicationRecord` objects, one per opportunity.
        """
        log.info("=" * 70)
        log.info("[bold magenta]AUTO-AGENT pipeline started[/]")
        if self._dry_run:
            log.info("[yellow]DRY-RUN mode – applications will NOT be submitted.[/]")
        log.info("=" * 70)

        # ── Step 1: Parse resume ────────────────────────────────────────────
        raw_text = self._fh.read_resume(resume_path)
        resume = self._parser.parse(raw_text)

        # ── Step 2: Search for opportunities ───────────────────────────────
        opportunities = self._searcher.search(resume, countries=countries)
        if not opportunities:
            log.warning("No opportunities found. Exiting pipeline.")
            return []

        records: list[ApplicationRecord] = []

        # ── Step 3: Process each opportunity ───────────────────────────────
        for opp in opportunities:
            log.info("-" * 60)
            log.info(
                "Processing: [bold cyan]%s[/] @ %s, %s",
                opp.title,
                opp.organization,
                opp.country,
            )

            record = ApplicationRecord(
                opportunity=opp,
                status=ApplicationStatus.JOBS_FOUND,
            )

            # ── 3a + 3b + 3c: Tailor → Score → Feedback loop ───────────────
            ats_feedback = None
            decision = FeedbackDecision.REFINE  # enter the loop on the first pass

            while decision == FeedbackDecision.REFINE:
                try:
                    tailored = self._tailor.tailor(resume, opp, ats_feedback=ats_feedback)
                    record.tailored_resume = tailored
                    record.status = ApplicationStatus.RESUME_TAILORED
                except Exception as exc:  # noqa: BLE001
                    record.status = ApplicationStatus.FAILED
                    record.error_message = f"Resume tailoring failed: {exc}"
                    log.error(record.error_message)
                    break

                try:
                    ats_result = self._ats.score(tailored, opp)
                    ats_feedback = ats_result
                except Exception as exc:  # noqa: BLE001
                    record.status = ApplicationStatus.FAILED
                    record.error_message = f"ATS scoring failed: {exc}"
                    log.error(record.error_message)
                    break

                decision, reason = self._feedback.evaluate(record, ats_result)

                if decision == FeedbackDecision.SKIP:
                    break  # record already marked SKIPPED by FeedbackLoopAgent

            # Skip to next opportunity if this one was skipped or errored
            if record.status in (ApplicationStatus.FAILED, ApplicationStatus.SKIPPED):
                records.append(record)
                continue

            # ── 3d: Cover letter ────────────────────────────────────────────
            try:
                cover = self._cover.generate(resume, opp, record.tailored_resume,
                                              profile=self._profile)
                record.cover_letter = cover
                record.status = ApplicationStatus.COVER_LETTER_DONE
            except Exception as exc:  # noqa: BLE001
                record.status = ApplicationStatus.FAILED
                record.error_message = f"Cover letter generation failed: {exc}"
                log.error(record.error_message)
                records.append(record)
                continue

            # ── 3e: Submit ──────────────────────────────────────────────────
            if self._dry_run:
                record.status = ApplicationStatus.SUBMITTED
                log.info(
                    "[yellow]DRY-RUN:[/] Would submit %s → %s",
                    opp.title,
                    opp.application_url,
                )
            else:
                self._submitter.submit(record)

            records.append(record)

        # ── Summary ─────────────────────────────────────────────────────────
        self._print_summary(records)
        return records

    # ------------------------------------------------------------------
    @staticmethod
    def _print_summary(records: list[ApplicationRecord]) -> None:
        submitted = sum(1 for r in records if r.status == ApplicationStatus.SUBMITTED)
        skipped   = sum(1 for r in records if r.status == ApplicationStatus.SKIPPED)
        failed    = sum(1 for r in records if r.status == ApplicationStatus.FAILED)

        log.info("=" * 70)
        log.info(
            "[bold magenta]Pipeline complete[/] – "
            "[green]submitted=%d[/]  [yellow]skipped=%d[/]  [red]failed=%d[/]  "
            "total=%d",
            submitted, skipped, failed, len(records),
        )
        log.info("=" * 70)

        for r in records:
            icon = {"submitted": "✓", "skipped": "⚠", "failed": "✗"}.get(
                r.status.value, "?"
            )
            ats = r.ats_result.score if r.ats_result else "N/A"
            log.info(
                "  %s  %-40s  %-12s  ATS: %s",
                icon,
                f"{r.opportunity.title[:38]}",
                r.opportunity.country,
                ats,
            )
