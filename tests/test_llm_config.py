import pytest

from src.config import LlmConfig


def test_ollama_config_validates_defaults():
    cfg = LlmConfig(
        provider="ollama",
        model="llama3.1:8b",
        temperature=0.2,
        max_tokens=512,
        timeout_s=60,
        ollama_base_url="http://localhost:11434/v1",
    )
    cfg.validate()  # should not raise


def test_unsupported_provider_is_rejected():
    cfg = LlmConfig(provider="openai")  # no longer supported
    with pytest.raises(ValueError):
        cfg.validate()


def test_ollama_requires_base_url():
    cfg = LlmConfig(provider="ollama", ollama_base_url="")
    with pytest.raises(ValueError):
        cfg.validate()


def test_none_provider_is_accepted():
    cfg = LlmConfig(provider="none", ollama_base_url="")
    cfg.validate()
