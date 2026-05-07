"""
Configuration for the AUTO-AGENT multi-agent internship application system.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM Settings ────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ─── ATS Settings ────────────────────────────────────────────────────────────
ATS_PASS_THRESHOLD: int = int(os.getenv("ATS_PASS_THRESHOLD", "75"))  # minimum score to proceed
ATS_MAX_RETRIES: int = int(os.getenv("ATS_MAX_RETRIES", "3"))          # max refinement loops

# ─── Search Settings ─────────────────────────────────────────────────────────
DEFAULT_COUNTRIES: list[str] = ["USA", "Canada", "Germany", "UK", "France",
                                 "Netherlands", "Sweden", "Switzerland", "Australia",
                                 "Japan", "Singapore"]
MAX_JOBS_PER_COUNTRY: int = int(os.getenv("MAX_JOBS_PER_COUNTRY", "10"))
SEARCH_TIMEOUT_SECONDS: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "30"))

# ─── Output Settings ─────────────────────────────────────────────────────────
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ─── Retry / Resilience ──────────────────────────────────────────────────────
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_WAIT_SECONDS: int = int(os.getenv("RETRY_WAIT_SECONDS", "2"))
