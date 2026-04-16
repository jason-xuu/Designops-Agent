"""Ollama LLM client using the OpenAI-compatible endpoint at /v1.

Mirrors the pattern used in ``prompt-reliability-lab/src/models/ollama_adapter.py``
and ``nl2geo-rhino-plugin/src/NL2Geo/Llm/OllamaClient.cs`` so all three projects
speak to the same local Ollama runtime in the same way.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from openai import OpenAI

from src.config import LlmConfig
from src.llm.client import LlmResponse

logger = logging.getLogger(__name__)


class OllamaClient:
    """Thin wrapper around Ollama's OpenAI-compatible /v1 endpoint."""

    provider_name = "ollama"

    def __init__(self, config: LlmConfig) -> None:
        self._config = config
        self.model = config.model
        self._client = OpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama",  # Ollama ignores the key but the OpenAI SDK requires one.
            timeout=config.timeout_s,
        )
        self.available = self._probe_available()

    # ------------------------------------------------------------------
    # Availability probe
    # ------------------------------------------------------------------

    def _probe_available(self) -> bool:
        """Return True if Ollama responds on /api/tags within a short timeout.

        Probing is cheap and non-blocking; if the daemon is down the agent
        transparently switches every node to its deterministic fallback.
        """
        probe_url = self._config.ollama_base_url.rstrip("/")
        if probe_url.endswith("/v1"):
            probe_url = probe_url[: -len("/v1")]
        try:
            resp = httpx.get(f"{probe_url}/api/tags", timeout=3.0)
            if resp.status_code != 200:
                logger.warning("Ollama probe non-200: %s", resp.status_code)
                return False
            tags = resp.json().get("models", [])
            names = {m.get("name", "") for m in tags}
            if self.model not in names and f"{self.model}:latest" not in names:
                logger.warning(
                    "Ollama model %r not found locally. Available: %s",
                    self.model,
                    sorted(names),
                )
                return False
            return True
        except Exception as exc:  # noqa: BLE001 — probe should never raise
            logger.warning("Ollama probe failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        expect_json: bool = True,
        retries: int = 2,
    ) -> LlmResponse:
        last_error: str | None = None

        for attempt in range(1, retries + 1):
            try:
                return self._call(
                    system_prompt, user_prompt, expect_json=expect_json, attempt=attempt
                )
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                wait = min(2 ** attempt, 8)
                logger.warning(
                    "Ollama error (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    retries,
                    last_error,
                    wait,
                )
                if attempt < retries:
                    time.sleep(wait)

        return LlmResponse(
            raw_response="",
            parsed=None,
            latency_ms=0.0,
            model=self.model,
            error=f"Exhausted {retries} retries. Last error: {last_error}",
            meta={"provider": self.provider_name, "attempts": retries},
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        expect_json: bool,
        attempt: int,
    ) -> LlmResponse:
        start = time.perf_counter()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000

        raw = response.choices[0].message.content or ""
        parsed = None
        error: str | None = None

        if expect_json:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                error = f"JSON parse error: {exc}"
                logger.warning("Ollama JSON parse failure: %s", raw[:200])

        return LlmResponse(
            raw_response=raw,
            parsed=parsed,
            latency_ms=round(elapsed_ms, 1),
            model=self.model,
            error=error,
            meta={"provider": self.provider_name, "attempts": attempt},
        )
