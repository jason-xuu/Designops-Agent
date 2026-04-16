"""No-op LLM client used when LLM_PROVIDER=none or Ollama is unreachable.

Keeps the agent runnable in CI and on machines without Ollama. Every call
returns an ``error`` response so the calling node falls through to its
deterministic path.
"""

from __future__ import annotations

from src.llm.client import LlmResponse


class NoopLlmClient:
    provider_name = "none"
    model = "noop"
    available = False

    def generate(
        self,
        system_prompt: str,  # noqa: ARG002
        user_prompt: str,  # noqa: ARG002
        *,
        expect_json: bool = True,  # noqa: ARG002
        retries: int = 2,  # noqa: ARG002
    ) -> LlmResponse:
        return LlmResponse(
            raw_response="",
            parsed=None,
            latency_ms=0.0,
            model=self.model,
            error="LLM disabled (provider=none or probe failed); using deterministic fallback.",
            meta={"provider": self.provider_name, "attempts": 0},
        )
