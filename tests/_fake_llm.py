"""Test double for :class:`LlmClient` used across LLM-node tests."""

from __future__ import annotations

import json
from typing import Any

from src.llm.client import LlmResponse


class FakeLlmClient:
    provider_name = "fake"
    model = "fake-model"

    def __init__(
        self,
        *,
        available: bool = True,
        payloads: list[Any] | None = None,
        errors: list[str | None] | None = None,
    ) -> None:
        self.available = available
        self._payloads = list(payloads or [])
        self._errors = list(errors or [])
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        expect_json: bool = True,
        retries: int = 2,
    ) -> LlmResponse:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "expect_json": expect_json,
                "retries": retries,
            }
        )
        payload = self._payloads.pop(0) if self._payloads else None
        error = self._errors.pop(0) if self._errors else None
        raw = json.dumps(payload) if payload is not None else ""
        return LlmResponse(
            raw_response=raw,
            parsed=payload,
            latency_ms=1.0,
            model=self.model,
            error=error,
            meta={"provider": self.provider_name, "attempts": 1},
        )
