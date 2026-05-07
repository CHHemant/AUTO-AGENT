"""
ApplicationSubmitterAgent
=========================
Role    : Submit the finalised application (tailored resume + cover letter) to
          the target organisation's portal or email address.
Input   : ApplicationRecord (with tailored resume, cover letter, opportunity)
Output  : Updated ApplicationRecord with submission status
Decision: Routes to the correct submission strategy (web portal, email, API)
          based on the opportunity's source field.

Note: Real portal automation (Selenium, Playwright) or email sending (SMTP)
      should be implemented inside the ``_submit_*`` methods.  The stubs below
      log what *would* happen so the rest of the pipeline is exercisable.
"""

from __future__ import annotations

from models import ApplicationRecord, ApplicationStatus
from utils.logger import get_logger

log = get_logger(__name__)


class ApplicationSubmitterAgent:
    """
    Handles the final submission step of the pipeline.

    Each ``_submit_*`` method represents a submission channel.  In production,
    replace the log statement with real automation code.
    """

    # Strategy registry: source tag → handler method name
    _STRATEGY_MAP: dict[str, str] = {
        "linkedin":  "_submit_linkedin",
        "indeed":    "_submit_indeed",
        "email":     "_submit_email",
        "sample":    "_submit_portal",
        "portal":    "_submit_portal",
    }

    # ------------------------------------------------------------------
    def submit(self, record: ApplicationRecord) -> ApplicationRecord:
        """
        Submit *record* using the appropriate channel.

        Updates ``record.status`` to SUBMITTED on success or FAILED on error
        and returns the mutated record.
        """
        opp = record.opportunity
        log.info(
            "[bold]ApplicationSubmitterAgent[/] – submitting to [cyan]%s[/] (%s)",
            opp.organization,
            opp.country,
        )

        if record.tailored_resume is None or record.cover_letter is None:
            record.status = ApplicationStatus.FAILED
            record.error_message = "Missing resume or cover letter – cannot submit."
            log.error(record.error_message)
            return record

        strategy_key = opp.source.lower() if opp.source else "portal"
        handler_name = self._STRATEGY_MAP.get(strategy_key, "_submit_portal")
        handler = getattr(self, handler_name)

        try:
            handler(record)
            record.status = ApplicationStatus.SUBMITTED
            log.info(
                "[green]✓ Application submitted:[/] %s @ %s",
                opp.title,
                opp.organization,
            )
        except Exception as exc:  # noqa: BLE001
            record.status = ApplicationStatus.FAILED
            record.error_message = str(exc)
            log.error("Submission failed for %s: %s", opp.title, exc)

        return record

    # ----------------------------------------------------------------- channels
    def _submit_portal(self, record: ApplicationRecord) -> None:
        """Submit via a generic web portal URL."""
        opp = record.opportunity
        log.info(
            "[dim]STUB[/] Portal submission → %s\n"
            "  Resume : %s\n"
            "  Letter : %s",
            opp.application_url,
            record.tailored_resume.file_path,  # type: ignore[union-attr]
            record.cover_letter.file_path,      # type: ignore[union-attr]
        )
        # TODO: Use Playwright/Selenium to automate form fill and file upload.

    def _submit_email(self, record: ApplicationRecord) -> None:
        """Submit via SMTP email."""
        opp = record.opportunity
        log.info(
            "[dim]STUB[/] Email submission → %s\n"
            "  Attachments: %s, %s",
            opp.application_url,
            record.tailored_resume.file_path,  # type: ignore[union-attr]
            record.cover_letter.file_path,      # type: ignore[union-attr]
        )
        # TODO: Use smtplib / SendGrid to send email with attachments.

    def _submit_linkedin(self, record: ApplicationRecord) -> None:
        """Submit via LinkedIn Easy Apply."""
        log.info(
            "[dim]STUB[/] LinkedIn Easy Apply → %s",
            record.opportunity.application_url,
        )
        # TODO: Use LinkedIn API or Playwright to fill Easy Apply form.

    def _submit_indeed(self, record: ApplicationRecord) -> None:
        """Submit via Indeed one-click apply."""
        log.info(
            "[dim]STUB[/] Indeed Apply → %s",
            record.opportunity.application_url,
        )
        # TODO: Use Indeed Publisher API or Playwright automation.
