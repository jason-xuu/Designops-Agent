from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class LlmConfig:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))


@dataclass(frozen=True)
class AppConfig:
    sqlite_path: Path = field(default_factory=lambda: PROJECT_ROOT / os.getenv("SQLITE_PATH", "designops_runs.db"))
    traces_dir: Path = PROJECT_ROOT / "traces"
    outputs_dir: Path = PROJECT_ROOT / "outputs"
    briefs_dir: Path = PROJECT_ROOT / "briefs"


def get_llm_config() -> LlmConfig:
    return LlmConfig()


def get_app_config() -> AppConfig:
    cfg = AppConfig()
    cfg.traces_dir.mkdir(parents=True, exist_ok=True)
    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    return cfg
