"""
Provider-agnostic LLM wrapper with retry logic.

Supported providers (set via ``LLM_PROVIDER`` env var):
  • openai    – OpenAI ChatCompletion  (requires ``OPENAI_API_KEY``)
  • anthropic – Anthropic Messages API (requires ``ANTHROPIC_API_KEY``)
  • google    – Google Gemini API      (requires ``GOOGLE_API_KEY``)

When the active provider's API key is absent the client operates in *mock*
mode, returning canned responses so the full pipeline can be exercised without
any live credentials.
"""

from __future__ import annotations

import json
import config as _cfg
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

_VALID_PROVIDERS = ("openai", "anthropic", "google")


class LLMClient:
    """
    Provider-agnostic wrapper around LLM chat completion APIs.

    Falls back to deterministic mock responses when the active provider's
    API key is absent.
    """

    def __init__(self) -> None:
        # Read config at construction time so test fixtures can patch _cfg
        self._provider = _cfg.LLM_PROVIDER.lower()
        if self._provider not in _VALID_PROVIDERS:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self._provider}'. "
                f"Valid choices: {', '.join(_VALID_PROVIDERS)}"
            )

        api_key = self._active_key()
        self._mock = not bool(api_key)

        if self._mock:
            log.warning(
                "No API key found for provider [bold yellow]%s[/] – "
                "running in [bold yellow]mock mode[/].",
                self._provider,
            )
        else:
            self._init_client(api_key)

    # ------------------------------------------------------------------
    def _active_key(self) -> str:
        """Return the API key for the currently configured provider."""
        if self._provider == "openai":
            return _cfg.OPENAI_API_KEY
        if self._provider == "anthropic":
            return _cfg.ANTHROPIC_API_KEY
        if self._provider == "google":
            return _cfg.GOOGLE_API_KEY
        return ""  # unreachable after provider validation

    def _init_client(self, api_key: str) -> None:
        """Initialise the provider-specific SDK client."""
        if self._provider == "openai":
            try:
                import openai  # noqa: PLC0415
                self._client = openai.OpenAI(api_key=api_key)
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for the OpenAI provider. "
                    "Run: pip install openai"
                ) from exc

        elif self._provider == "anthropic":
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.Anthropic(api_key=api_key)
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required for the Anthropic provider. "
                    "Run: pip install anthropic"
                ) from exc

        elif self._provider == "google":
            try:
                import google.generativeai as genai  # noqa: PLC0415
                genai.configure(api_key=api_key)
                self._client = genai
            except ImportError as exc:
                raise ImportError(
                    "google-generativeai package is required for the Google provider. "
                    "Run: pip install google-generativeai"
                ) from exc

    # ------------------------------------------------------------------
    def complete(self, system_prompt: str, user_prompt: str, task_key: str = "default") -> str:
        """
        Send a chat completion request and return the assistant's reply.

        Parameters
        ----------
        system_prompt : str  Role/instruction context for the model.
        user_prompt   : str  The actual request.
        task_key      : str  Key used to look up mock responses in mock mode.
        """
        if self._mock:
            response = _MOCK_RESPONSES.get(task_key, _MOCK_RESPONSES["default"])
            log.debug("[dim]Mock response for task_key=%s[/]", task_key)
            return response

        return self._call_api(system_prompt, user_prompt)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(_cfg.MAX_RETRIES),
        wait=wait_exponential(multiplier=_cfg.RETRY_WAIT_SECONDS, min=1, max=30),
        reraise=True,
    )
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Route to the appropriate provider backend with exponential back-off retry."""
        if self._provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        if self._provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        if self._provider == "google":
            return self._call_google(system_prompt, user_prompt)
        raise RuntimeError(f"No backend for provider '{self._provider}'")  # pragma: no cover

    # ------------------------------------------------------------------ backends
    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=_cfg.LLM_MODEL,
            temperature=_cfg.LLM_TEMPERATURE,
            max_tokens=_cfg.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=_cfg.LLM_MODEL,
            max_tokens=_cfg.LLM_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text if response.content else ""

    def _call_google(self, system_prompt: str, user_prompt: str) -> str:
        import google.generativeai as genai  # noqa: PLC0415
        model = genai.GenerativeModel(
            model_name=_cfg.LLM_MODEL,
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_prompt)
        return response.text if response.text else ""
