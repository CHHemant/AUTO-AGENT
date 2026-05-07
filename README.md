# AUTO-AGENT — Automated Research Internship Application System

A **multi-agent AI system** that takes a single resume and automatically applies
for research internships abroad (USA, Canada, Germany, UK, France, and more) by
generating ATS-friendly tailored resumes and personalised cover letters for each
role.

---

## System Architecture

```
User Input (resume + countries)
        │
        ▼
┌─────────────────────┐
│  ORCHESTRATOR AGENT │  ◄── routes tasks, manages feedback loops & retries
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │ Agent 1     │  ResumeParserAgent      – extract structured data from resume
    │ Agent 2     │  InternshipSearchAgent  – find opportunities per country
    │             │
    │  ┌─ loop ─┐ │
    │  │Agent 3 │ │  ResumeTailoringAgent   – ATS-optimised resume (DOCX)
    │  │Agent 4 │ │  ATSScorerAgent         – score 0–100 + keyword gap list
    │  │Agent 5 │ │  FeedbackLoopAgent      – ACCEPT / REFINE / SKIP decision
    │  └────────┘ │      └─ REFINE → back to Agent 3 (up to 3 retries)
    │             │
    │ Agent 6     │  CoverLetterAgent       – country-specific cover letter (DOCX)
    │ Agent 7     │  ApplicationSubmitter   – portal / email / LinkedIn / Indeed
    └─────────────┘
```

Full ASCII flowchart (with error-handling and scalability notes):

```
python main.py --flowchart
```

---

## Agents

| # | Agent | Input | Output | Decision Logic |
|---|-------|-------|--------|----------------|
| 1 | **ResumeParserAgent** | Raw resume text | `ResumeData` | LLM JSON extraction; regex fallback |
| 2 | **InternshipSearchAgent** | `ResumeData` + countries | `List[InternshipOpportunity]` | Keyword-overlap relevance ranking; capped per country |
| 3 | **ResumeTailoringAgent** | `ResumeData` + opportunity + ATS feedback | `TailoredResume` (DOCX) | LLM rewrites resume; injects JD keywords; standard ATS-safe headings |
| 4 | **ATSScorerAgent** | `TailoredResume` + opportunity | `ATSResult` (score 0–100) | LLM ATS simulation; rule-based keyword-overlap fallback |
| 5 | **FeedbackLoopAgent** | `ATSResult` + retry count | Decision: ACCEPT / REFINE / SKIP | score ≥ threshold → ACCEPT; score < threshold + retries left → REFINE; else SKIP |
| 6 | **CoverLetterAgent** | `ResumeData` + opportunity + tailored resume | `CoverLetter` (DOCX) | Country-specific tone; word-limit enforcement |
| 7 | **ApplicationSubmitterAgent** | `ApplicationRecord` | Submission status | Route by source: portal / email / LinkedIn / Indeed |

---

## Feedback Loop & Error Handling

```
ResumeTailor  →  ATSScorer  →  FeedbackLoop
      ▲               │              │
      └───── REFINE ──┘   score < 75 & retries < 3
                           ACCEPT    score ≥ 75
                           SKIP      retries ≥ 3
```

| Agent | Error | Recovery |
|-------|-------|----------|
| ResumeParser | JSON decode failure | Regex-based fallback |
| InternshipSearch | Network / API error | Fall back to sample dataset |
| ResumeTailor | LLM timeout | Exponential back-off retry (tenacity) |
| ATSScorer | JSON decode failure | Rule-based keyword-overlap scorer |
| FeedbackLoop | Score below threshold | Inject feedback into next tailor prompt |
| CoverLetter | LLM error | Retry; mark FAILED if persistent |
| Submitter | Network / portal error | Mark FAILED; log full trace |

---

## Scalability

- **Stateless agents** – no mutable state between calls; safe for thread-pool/async execution.
- **Dependency injection** – `LLMClient` is injected → swap model without touching agents.
- **Config-driven** – all thresholds and limits live in `config.py` / `.env`.
- **Isolated output** – each opportunity gets its own sub-folder under `output/`.
- **Pluggable search** – `InternshipSearchAgent._live_search()` is a thin shim; real API clients plug in without changing other agents.
- **Queue-based scale** – wrap the per-opportunity loop in Celery / RQ / asyncio to process thousands of jobs in parallel.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure (optional – works in mock mode without a key)

```bash
cp .env.example .env   # then add your OPENAI_API_KEY
```

### 3. Print the flowchart

```bash
python main.py --flowchart
```

### 4. Run the pipeline (dry-run, no actual submissions)

```bash
python main.py --resume path/to/your_resume.pdf --countries USA Canada Germany
```

### 5. Run with live submission

```bash
python main.py --resume path/to/your_resume.pdf --countries USA Germany --no-dry-run
```

---

## Project Structure

```
AUTO-AGENT/
├── main.py                        # CLI entry point
├── config.py                      # All configuration constants
├── flowchart.py                   # ASCII architecture flowchart
├── models.py                      # Shared data models (dataclasses)
├── requirements.txt
├── agents/
│   ├── orchestrator.py            # OrchestratorAgent  (pipeline controller)
│   ├── resume_parser.py           # ResumeParserAgent
│   ├── internship_search.py       # InternshipSearchAgent
│   ├── resume_tailor.py           # ResumeTailoringAgent
│   ├── ats_scorer.py              # ATSScorerAgent
│   ├── cover_letter.py            # CoverLetterAgent
│   ├── application_submitter.py   # ApplicationSubmitterAgent
│   └── feedback_loop.py           # FeedbackLoopAgent
├── utils/
│   ├── llm_client.py              # OpenAI wrapper (mock mode when no key)
│   ├── file_handler.py            # PDF/DOCX read; DOCX write
│   └── logger.py                  # Rich-formatted logger
└── tests/
    ├── conftest.py                 # Shared fixtures
    ├── test_resume_parser.py
    ├── test_internship_search.py
    ├── test_ats_scorer.py
    ├── test_feedback_loop.py
    ├── test_resume_tailor.py
    ├── test_cover_letter.py
    └── test_orchestrator.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

All 49 tests pass without an OpenAI API key (mock mode).
