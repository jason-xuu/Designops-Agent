"""Construct an :class:`LlmClient` from runtime configuration."""

from __future__ import annotations

import logging

from src.config import LlmConfig, get_llm_config
from src.llm.client import LlmClient
from src.llm.noop_client import NoopLlmClient
from src.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


def create_llm_client(config: LlmConfig | None = None) -> LlmClient:
    """Return an :class:`LlmClient` that matches ``config.provider``.

    When the configured provider is unreachable (e.g. Ollama daemon not
    running) this returns a :class:`NoopLlmClient` so downstream nodes
    transparently fall back to their deterministic implementations.
    """
    cfg = config or get_llm_config()
    if cfg.provider == "none":
        logger.info("LLM provider disabled (LLM_PROVIDER=none). Using deterministic fallback.")
        return NoopLlmClient()

    if cfg.provider == "ollama":
        client = OllamaClient(cfg)
        if not client.available:
            logger.warning(
                "Ollama at %s not serving %s; falling back to NoopLlmClient.",
                cfg.ollama_base_url,
                cfg.model,
            )
            return NoopLlmClient()
        logger.info("Using Ollama model %s at %s.", cfg.model, cfg.ollama_base_url)
        return client

    raise ValueError(f"Unsupported LLM provider: {cfg.provider!r}")
