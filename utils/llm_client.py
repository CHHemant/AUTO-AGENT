"""
Thin wrapper around the OpenAI chat completion API with retry logic.

When OPENAI_API_KEY is not set the client operates in *mock* mode and returns
canned responses so the rest of the system can be exercised without a live key.
"""

from __future__ import annotations

import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    OPENAI_API_KEY,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    MAX_RETRIES,
    RETRY_WAIT_SECONDS,
)
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Mock responses used when no API key is available
# ---------------------------------------------------------------------------
_MOCK_RESPONSES: dict[str, str] = {
    "parse_resume": json.dumps({
        "full_name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0100",
        "linkedin": "linkedin.com/in/janedoe",
        "github": "github.com/janedoe",
        "summary": "PhD student in Computer Science specialising in machine learning.",
        "education": [{"degree": "B.Sc. Computer Science", "institution": "MIT", "year": "2023"}],
        "experience": [{"title": "Research Intern", "org": "Google Brain", "duration": "Summer 2022",
                        "description": "Worked on NLP models."}],
        "skills": ["Python", "PyTorch", "TensorFlow", "NLP", "Deep Learning"],
        "publications": ["Doe et al. (2023). Fast Attention. ArXiv."],
        "projects": [{"name": "Auto-ML", "description": "Automated hyper-parameter tuning tool."}],
        "certifications": [],
        "languages": ["English", "German"],
    }),
    "tailor_resume": (
        "TAILORED RESUME\n"
        "Jane Doe | jane.doe@example.com\n\n"
        "SUMMARY\nExperienced ML researcher seeking a research internship.\n\n"
        "SKILLS\nPython, PyTorch, TensorFlow, NLP, Deep Learning\n"
    ),
    "cover_letter": (
        "Dear Hiring Manager,\n\n"
        "I am writing to express my strong interest in the Research Intern position at "
        "your organisation. My background in deep learning and NLP aligns closely with "
        "your team's research direction.\n\n"
        "Sincerely,\nJane Doe"
    ),
    "ats_score": json.dumps({
        "score": 82,
        "matched_keywords": ["Python", "deep learning", "NLP"],
        "missing_keywords": ["PyTorch", "transformer"],
        "suggestions": ["Add PyTorch to skills section.", "Mention transformer architecture experience."],
    }),
    "default": "Mock LLM response.",
}


class LLMClient:
    """
    Wrapper around OpenAI ChatCompletion.

    Falls back to deterministic mock responses when OPENAI_API_KEY is absent.
    """

    def __init__(self) -> None:
        self._mock = not bool(OPENAI_API_KEY)
        if self._mock:
            log.warning("OPENAI_API_KEY not set – running in [bold yellow]mock mode[/].")
        else:
            try:
                import openai
                self._client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except ImportError as exc:
                raise ImportError("openai package is required. Run: pip install openai") from exc

    # ------------------------------------------------------------------
    def complete(self, system_prompt: str, user_prompt: str, task_key: str = "default") -> str:
        """
        Send a chat completion request and return the assistant's reply as a string.

        Parameters
        ----------
        system_prompt : str  Role/instruction context for the model.
        user_prompt   : str  The actual request.
        task_key      : str  Key used to look up mock responses when in mock mode.
        """
        if self._mock:
            response = _MOCK_RESPONSES.get(task_key, _MOCK_RESPONSES["default"])
            log.debug("[dim]Mock response for task_key=%s[/]", task_key)
            return response

        return self._call_api(system_prompt, user_prompt)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_WAIT_SECONDS, min=1, max=30),
        reraise=True,
    )
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call the OpenAI API with exponential back-off retry."""
        import openai  # noqa: PLC0415

        response = self._client.chat.completions.create(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
