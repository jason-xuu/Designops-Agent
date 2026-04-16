"""LLM client protocol and response shape shared across the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class LlmResponse:
    """Normalized response returned by every :class:`LlmClient`.

    Attributes
    ----------
    raw_response
        Full assistant message text.
    parsed
        Parsed JSON payload when ``expect_json=True``. ``None`` on parse
        failure or non-JSON calls.
    latency_ms
        Round-trip time in milliseconds.
    model
        Model identifier that served the response.
    error
        Human-readable error message, or ``None`` on success.
    meta
        Additional provenance (provider name, attempts used, etc.).
    """

    raw_response: str = ""
    parsed: Any | None = None
    latency_ms: float = 0.0
    model: str = ""
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


@runtime_checkable
class LlmClient(Protocol):
    """Minimal contract the agent nodes depend on."""

    provider_name: str
    model: str
    available: bool

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        expect_json: bool = True,
        retries: int = 2,
    ) -> LlmResponse: ...
