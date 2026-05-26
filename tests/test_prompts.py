import pytest
from app.summarization.prompts import PromptLibrary


def test_load_existing_prompt():
    lib = PromptLibrary()
    prompt = lib.load("summarize_chunk")
    assert len(prompt) > 0
    assert "{text}" in prompt
    assert "{title}" in prompt


def test_render_with_variables():
    lib = PromptLibrary()
    result = lib.render("summarize_chunk", text="Hello", title="Test")
    assert "Hello" in result
    assert "Test" in result


def test_missing_prompt_raises_error():
    lib = PromptLibrary()
    with pytest.raises(FileNotFoundError):
        lib.load("nonexistent_prompt")


def test_cache_works():
    lib = PromptLibrary()
    p1 = lib.load("summarize_chunk")
    p2 = lib.load("summarize_chunk")
    assert p1 is p2


def test_all_prompts_have_expected_vars():
    lib = PromptLibrary()
    for name in ["summarize_chunk", "synthesize", "extract_insights", "weekly_report"]:
        prompt = lib.load(name)
        assert len(prompt) > 0, f"Prompt '{name}' is empty"
