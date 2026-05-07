# AUTO-AGENT — Automated Research Internship Application System

A **multi-agent AI system** that takes a single resume and automatically applies
for research internships abroad (USA, Canada, Germany, UK, France, and more) by
generating ATS-friendly tailored resumes and personalised cover letters for each
role.

Supports **OpenAI**, **Anthropic (Claude)**, and **Google Gemini** as LLM
backends — choose the provider that matches your API key, or run entirely in
mock mode with no key at all.

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
| 6 | **CoverLetterAgent** | `ResumeData` + opportunity + tailored resume + `UserProfile` | `CoverLetter` (DOCX) | Country-specific tone; word-limit enforcement; profile details injected |
| 7 | **ApplicationSubmitterAgent** | `ApplicationRecord` | Submission status | Route by source: portal / email / LinkedIn / Indeed |

---

## Supported LLM Providers

| Provider | Env var | Default model | Free tier? |
|----------|---------|---------------|-----------|
| **OpenAI** (default) | `OPENAI_API_KEY` | `gpt-4o` | No (credits expire) |
| **Anthropic Claude** | `ANTHROPIC_API_KEY` | `claude-opus-4-5` | No – pay-as-you-go |
| **Google Gemini** | `GOOGLE_API_KEY` | `gemini-1.5-pro` | Yes – Gemini API free tier |

> **Note on free tiers**: Google Gemini offers a free API quota that is enough
> for testing. OpenAI and Anthropic offer free trial credits but no ongoing
> free tier. All three providers require you to create an account and generate
> an API key on their official website:
>
> - OpenAI    : <https://platform.openai.com/api-keys>
> - Anthropic : <https://console.anthropic.com/settings/keys>
> - Google    : <https://aistudio.google.com/app/apikey>

Override the model for any provider with `LLM_MODEL`:

```bash
LLM_MODEL=claude-haiku-4-5 python main.py --provider anthropic --resume my_resume.pdf
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your API key

Copy the example env file and add **one** key:

```bash
cp .env.example .env
```

Then edit `.env` – uncomment and fill in only the provider you plan to use:

```dotenv
# ── Choose ONE provider ──────────────────────────────────
LLM_PROVIDER=openai          # openai | anthropic | google

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic Claude
# ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini (has a free tier)
# GOOGLE_API_KEY=AIza...
```

Works in **mock mode** with no key at all — great for testing the pipeline
without spending any API credits.

### 3. Set up your applicant profile (first run only)

```bash
python main.py --setup
```

You will be asked for:
- Full name, email, phone
- LinkedIn URL, GitHub URL, portfolio URL
- Work authorisation (e.g. "US Citizen", "Requires visa sponsorship")
- Location preference (Remote / On-site / Hybrid)
- Notice period
- Whether you are willing to relocate
- Target roles and preferred countries

Answers are saved to `~/.auto-agent-profile.json` and reused on every
subsequent run. Re-run `--setup` at any time to update them.

### 4. Print the flowchart

```bash
python main.py --flowchart
```

### 5. Run the pipeline (dry-run, no actual submissions)

```bash
python main.py --resume path/to/your_resume.pdf --countries USA Canada Germany
```

### 6. Select a specific LLM provider via CLI

```bash
# Use Anthropic Claude (ANTHROPIC_API_KEY must be set)
python main.py --resume resume.pdf --provider anthropic

# Use Google Gemini (GOOGLE_API_KEY must be set, free tier available)
python main.py --resume resume.pdf --provider google

# Use OpenAI (default, OPENAI_API_KEY must be set)
python main.py --resume resume.pdf --provider openai
```

### 7. Run with live submission

```bash
python main.py --resume path/to/your_resume.pdf --countries USA Germany --no-dry-run
```

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

## Project Structure

```
AUTO-AGENT/
├── main.py                        # CLI entry point
├── config.py                      # All configuration constants
├── flowchart.py                   # ASCII architecture flowchart
├── models.py                      # Shared data models (dataclasses, incl. UserProfile)
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
│   ├── llm_client.py              # Multi-provider LLM wrapper (OpenAI/Anthropic/Google)
│   ├── user_profile.py            # Applicant profile: collect, validate, persist
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
    ├── test_orchestrator.py
    ├── test_llm_client.py          # Multi-provider + mock mode tests
    └── test_user_profile.py        # Profile validation, load/save, onboarding tests
```

---

## Running Tests

```bash
pytest tests/ -v
```

All 87 tests pass without any API key (mock mode).

