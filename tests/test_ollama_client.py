"""Integration-lite tests for :class:`OllamaClient`.

These use ``monkeypatch`` to avoid touching the real Ollama daemon or the
network. The point is to verify the adapter shape: probe logic, JSON
parsing, retry behavior, and error normalization.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.config import LlmConfig
from src.llm import create_llm_client
from src.llm.noop_client import NoopLlmClient
from src.llm.ollama_client import OllamaClient


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        message = SimpleNamespace(content=item)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _make_client(monkeypatch, probe_ok=True, responses=None):
    cfg = LlmConfig(
        provider="ollama",
        model="llama3.1:8b",
        temperature=0.0,
        max_tokens=64,
        timeout_s=5,
        ollama_base_url="http://localhost:11434/v1",
    )

    class _FakeResp:
        status_code = 200 if probe_ok else 500

        @staticmethod
        def json():
            return {"models": [{"name": "llama3.1:8b"}]}

    def fake_get(url, timeout):  # noqa: ARG001
        return _FakeResp()

    import src.llm.ollama_client as ollama_module

    monkeypatch.setattr(ollama_module.httpx, "get", fake_get)

    client = OllamaClient(cfg)
    fake_chat = _FakeCompletions(responses or [])
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=fake_chat)
    )
    return client, fake_chat


def test_ollama_client_parses_json_response(monkeypatch):
    payload = json.dumps({"ok": True, "n": 3})
    client, chat = _make_client(monkeypatch, responses=[payload])
    assert client.available is True

    resp = client.generate("sys", "user", expect_json=True, retries=1)
    assert resp.ok
    assert resp.parsed == {"ok": True, "n": 3}
    assert resp.raw_response == payload
    assert chat.calls[0]["model"] == "llama3.1:8b"
    assert chat.calls[0]["response_format"] == {"type": "json_object"}


def test_ollama_client_reports_json_parse_error(monkeypatch):
    client, _ = _make_client(monkeypatch, responses=["not-json"])
    resp = client.generate("sys", "user", expect_json=True, retries=1)
    assert resp.raw_response == "not-json"
    assert resp.parsed is None
    assert resp.error and "JSON parse error" in resp.error


def test_ollama_client_retries_then_fails(monkeypatch):
    client, _ = _make_client(
        monkeypatch,
        responses=[RuntimeError("boom1"), RuntimeError("boom2")],
    )
    resp = client.generate("sys", "user", expect_json=True, retries=2)
    assert not resp.ok
    assert "Exhausted" in (resp.error or "")


def test_factory_returns_noop_when_probe_fails(monkeypatch):
    cfg = LlmConfig(
        provider="ollama",
        model="llama3.1:8b",
        ollama_base_url="http://localhost:11434/v1",
    )

    class _BadResp:
        status_code = 500

        @staticmethod
        def json():
            return {}

    import src.llm.ollama_client as ollama_module

    monkeypatch.setattr(ollama_module.httpx, "get", lambda url, timeout: _BadResp())

    client = create_llm_client(cfg)
    assert isinstance(client, NoopLlmClient)


def test_factory_returns_noop_when_provider_is_none():
    cfg = LlmConfig(provider="none", ollama_base_url="")
    client = create_llm_client(cfg)
    assert isinstance(client, NoopLlmClient)


def test_factory_rejects_unknown_provider():
    cfg = LlmConfig(provider="gemini", ollama_base_url="x")
    with pytest.raises(ValueError):
        create_llm_client(cfg)
