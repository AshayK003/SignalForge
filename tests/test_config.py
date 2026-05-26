import os
import pytest
from app.utils.config import Config, load_config


def test_default_config_has_expected_keys():
    cfg = Config()
    assert cfg.app.name == "SignalForge"
    assert cfg.chunking.max_chunk_size == 3000
    assert cfg.transcription.model == "base"
    assert cfg.llm.provider == "openrouter"


def test_load_config_returns_config_object():
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.app.name == "SignalForge"


def test_env_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    cfg = load_config()
    assert cfg.llm.provider == "ollama"
    assert cfg.llm.ollama_model == "llama3.2"


def test_openrouter_missing_key_warns():
    cfg = Config()
    cfg.llm.provider = "openrouter"
    cfg.llm.openrouter_api_key = ""
    assert cfg.llm.openrouter_api_key == ""
    assert cfg.llm.provider == "openrouter"
