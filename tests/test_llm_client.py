import pytest
from app.summarization.llm_client import LLMClient, _MAX_RETRIES
from app.utils.config import Config


def test_client_initialization():
    cfg = Config()
    client = LLMClient(cfg)
    assert client._provider_model("openrouter") == cfg.llm.openrouter_model
    assert "openrouter" in client._provider_base_url("openrouter")


def test_client_ollama_config():
    cfg = Config()
    cfg.llm.provider = "ollama"
    cfg.llm.ollama_base_url = "http://localhost:11434"
    cfg.llm.ollama_model = "llama3.2"
    client = LLMClient(cfg)
    assert client._provider_model("ollama") == "llama3.2"
    assert "localhost:11434" in client._provider_base_url("ollama")


def test_supports_json_mode():
    cfg = Config()
    cfg.llm.provider = "openrouter"
    client = LLMClient(cfg)
    assert client.supports_json_mode() is True

    cfg.llm.provider = "ollama"
    client = LLMClient(cfg)
    assert client.supports_json_mode() is False


def test_fallback_provider_ollama_when_openrouter_fails():
    cfg = Config()
    cfg.llm.provider = "openrouter"
    cfg.llm.openrouter_model = "nonexistent-model"
    client = LLMClient(cfg)
    assert client._fallback_provider() == "ollama"


def test_fallback_provider_openrouter_when_ollama_fails():
    cfg = Config()
    cfg.llm.provider = "ollama"
    cfg.llm.openrouter_api_key = "test-key"
    client = LLMClient(cfg)
    assert client._fallback_provider() == "openrouter"


def test_no_fallback_when_ollama_primary_and_no_openrouter_key():
    cfg = Config()
    cfg.llm.provider = "ollama"
    cfg.llm.openrouter_api_key = ""
    client = LLMClient(cfg)
    assert client._fallback_provider() is None
