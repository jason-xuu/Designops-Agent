"""LLM clients for DesignOps Agent.

Exposes a minimal :class:`LlmClient` protocol and an Ollama-backed
implementation. All node LLM calls go through this boundary so the agent
can fall back to deterministic behavior when Ollama is unreachable.
"""

from src.llm.client import LlmClient, LlmResponse
from src.llm.factory import create_llm_client
from src.llm.noop_client import NoopLlmClient
from src.llm.ollama_client import OllamaClient

__all__ = [
    "LlmClient",
    "LlmResponse",
    "NoopLlmClient",
    "OllamaClient",
    "create_llm_client",
]
