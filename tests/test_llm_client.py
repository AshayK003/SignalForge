import pytest
from app.summarization.llm_client import LLMClient
from app.utils.config import Config


def test_client_initialization():
    cfg = Config()
    client = LLMClient(cfg)
    assert client._model == cfg.llm.openrouter_model
    assert "openrouter" in client._base_url


def test_client_ollama_config():
    cfg = Config()
    cfg.llm.provider = "ollama"
    cfg.llm.ollama_base_url = "http://localhost:11434"
    cfg.llm.ollama_model = "llama3.2"
    client = LLMClient(cfg)
    assert client._model == "llama3.2"
    assert "localhost:11434" in client._base_url


def test_supports_json_mode():
    cfg = Config()
    cfg.llm.provider = "openrouter"
    client = LLMClient(cfg)
    assert client.supports_json_mode() is True

    cfg.llm.provider = "ollama"
    client = LLMClient(cfg)
    assert client.supports_json_mode() is False
