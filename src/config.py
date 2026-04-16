"""Configuration for DesignOps Agent.

All runtime settings are loaded from environment variables. The default
provider is Ollama (OpenAI-compatible endpoint on localhost:11434), which
matches the pattern used in `prompt-reliability-lab` and `nl2geo-rhino-plugin`
and keeps the agent runnable locally with no API key or network egress.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LlmConfig:
    """Runtime configuration for the LLM backend.

    provider
        One of ``"ollama"`` or ``"none"``. When ``"none"``, every node runs
        its deterministic fallback path and no HTTP calls are made.
    """

    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama").lower())
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3.1:8b"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1024")))
    timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_S", "180")))
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    )

    def validate(self) -> None:
        allowed = {"ollama", "none"}
        if self.provider not in allowed:
            raise ValueError(
                f"Unsupported LLM_PROVIDER={self.provider!r}. Supported values: {sorted(allowed)}."
            )
        if self.provider == "ollama":
            if not self.ollama_base_url:
                raise ValueError("OLLAMA_BASE_URL must be set when LLM_PROVIDER=ollama.")
            if not self.model:
                raise ValueError("LLM_MODEL must be set when LLM_PROVIDER=ollama.")


@dataclass(frozen=True)
class AppConfig:
    sqlite_path: Path = field(
        default_factory=lambda: PROJECT_ROOT / os.getenv("SQLITE_PATH", "designops_runs.db")
    )
    traces_dir: Path = PROJECT_ROOT / "traces"
    outputs_dir: Path = PROJECT_ROOT / "outputs"
    briefs_dir: Path = PROJECT_ROOT / "briefs"


def get_llm_config() -> LlmConfig:
    cfg = LlmConfig()
    cfg.validate()
    return cfg


def get_app_config() -> AppConfig:
    cfg = AppConfig()
    cfg.traces_dir.mkdir(parents=True, exist_ok=True)
    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
