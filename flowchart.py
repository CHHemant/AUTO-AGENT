"""
flowchart.py – ASCII flowchart of the AUTO-AGENT multi-agent pipeline.

Run directly to print the flowchart:
    python flowchart.py
"""

FLOWCHART = r"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                      AUTO-AGENT  Multi-Agent Pipeline                          ║
║            Automated Research Internship Application System                    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  USER INPUT                                                                  │
 │  • Resume file (.pdf / .docx / .txt)                                         │
 │  • Target countries  (USA, Canada, Germany, UK, France, …)                   │
 │  • Research area preferences  (optional)                                     │
 └──────────────────────────────┬───────────────────────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  ORCHESTRATOR AGENT  ◄──────────────────────── Feedback / Error Signals      │
 │  Role   : Pipeline controller & task router                                  │
 │  Input  : Resume path, countries, preferences                                │
 │  Output : List[ApplicationRecord] (full audit trail)                         │
 │  Logic  : Coordinates all agents; retries on ATS failure; skips on timeout   │
 └──────────────────────────────┬───────────────────────────────────────────────┘
                                │
              ┌─────────────────┘
              │
              ▼
 ┌─────────────────────────────────┐
 │  AGENT 1 · RESUME PARSER        │
 │  Input : Raw resume text        │
 │  Output: ResumeData             │
 │   • full_name, email, phone     │
 │   • education, experience       │
 │   • skills, publications        │
 │   • projects, certifications    │
 │  Logic : LLM JSON extraction;   │
 │          regex fallback on fail │
 └──────────────┬──────────────────┘
                │  ResumeData
                ▼
 ┌─────────────────────────────────┐
 │  AGENT 2 · INTERNSHIP SEARCH    │
 │  Input : ResumeData + countries │
 │  Output: List[Opportunity]      │
 │  Logic : Query job boards /     │
 │          sample data; filter    │
 │          by keyword relevance;  │
 │          cap per country        │
 └──────────────┬──────────────────┘
                │  List[InternshipOpportunity]
                ▼
 ╔══════════════════════════════════════════╗
 ║  FOR EACH OPPORTUNITY                    ║
 ╚══════════════════════╤═══════════════════╝
                        │
                        ▼
         ┌──────────────────────────────────┐
         │  AGENT 3 · RESUME TAILOR         │
         │  Input : ResumeData + Opp        │
         │          + ATSFeedback (retry)   │
         │  Output: TailoredResume (DOCX)   │
         │  Logic : LLM rewrites resume;    │
         │          injects JD keywords;    │
         │          formats for ATS         │
         └──────────────┬───────────────────┘
                        │  TailoredResume
                        ▼
         ┌──────────────────────────────────┐
         │  AGENT 4 · ATS SCORER            │
         │  Input : TailoredResume + Opp    │
         │  Output: ATSResult               │
         │   • score 0–100                  │
         │   • matched / missing keywords   │
         │   • actionable suggestions       │
         │  Logic : LLM simulation +        │
         │          keyword-overlap fallback│
         └──────────────┬───────────────────┘
                        │  ATSResult
                        ▼
         ┌──────────────────────────────────┐
         │  AGENT 5 · FEEDBACK LOOP         │
         │  Input : ATSResult + record      │
         │  Decision tree:                  │
         │                                  │
         │  score ≥ threshold  ──► ACCEPT   │
         │  score <  threshold              │
         │    retries < max   ──► REFINE ───┼──► back to AGENT 3
         │    retries ≥ max   ──► SKIP      │
         └──────────────┬───────────────────┘
                        │  ACCEPT
                        ▼
         ┌──────────────────────────────────┐
         │  AGENT 6 · COVER LETTER          │
         │  Input : ResumeData + Opp +      │
         │          TailoredResume          │
         │  Output: CoverLetter (DOCX)      │
         │  Logic : LLM generates letter;   │
         │          country-specific tone;  │
         │          word-limit enforcement  │
         └──────────────┬───────────────────┘
                        │  CoverLetter
                        ▼
         ┌──────────────────────────────────┐
         │  AGENT 7 · APPLICATION SUBMITTER │
         │  Input : TailoredResume +        │
         │          CoverLetter + Opp       │
         │  Output: ApplicationRecord       │
         │          (status = SUBMITTED)    │
         │  Logic : Route by source:        │
         │   • Portal  → web form upload    │
         │   • Email   → SMTP attachment    │
         │   • LinkedIn→ Easy Apply API     │
         │   • Indeed  → Publisher API      │
         └──────────────┬───────────────────┘
                        │
 ╔══════════════════════╧═══════════════════╗
 ║  END OF OPPORTUNITY LOOP                 ║
 ╚══════════════════════════════════════════╝
                        │
                        ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  SUMMARY REPORT                                                              │
 │  • Total applications submitted / skipped / failed                           │
 │  • ATS scores per application                                                │
 │  • Paths to generated DOCX files                                             │
 └──────────────────────────────────────────────────────────────────────────────┘

═══════════════════════  ERROR HANDLING STRATEGY  ═══════════════════════════════

  Agent              Error Type               Recovery
  ──────────────────────────────────────────────────────────────────────────────
  ResumeParser       JSON decode failure      Regex-based fallback extraction
  InternshipSearch   Network / API error      Fall back to sample dataset
  ResumeTailor       LLM API timeout          Retry up to MAX_RETRIES with
                                              exponential back-off (tenacity)
  ATSScorer          JSON decode failure      Rule-based keyword-overlap scorer
  FeedbackLoop       Score below threshold    Inject ATSResult into next tailor
                                              prompt; skip after ATS_MAX_RETRIES
  CoverLetter        LLM error                Retry; mark FAILED if persistent
  Submitter          Network / portal error   Mark record FAILED; log full trace

═══════════════════════  SCALABILITY DESIGN  ════════════════════════════════════

  • Stateless agents  : Each agent holds no mutable state between calls; safe
                        for concurrent execution (thread pool / async).
  • Dependency inject : LLMClient injected at construction → swap for any model.
  • Config-driven     : All thresholds / limits in config.py or .env file.
  • Output dir        : Each opportunity gets its own sub-folder under output/.
  • Extensible search : InternshipSearchAgent._live_search() is a thin shim;
                        real API clients plug in without touching other agents.
  • Queue-based scale : Wrap the per-opportunity loop in a job queue (Celery /
                        RQ / asyncio) to process thousands of jobs in parallel.
"""


def print_flowchart() -> None:
    """Print the ASCII flowchart to stdout."""
    print(FLOWCHART)


if __name__ == "__main__":
    print_flowchart()
