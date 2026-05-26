import pytest
from app.summarization.chunker import chunk_text


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text(None) == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "Hello world."
    chunks = chunk_text(text, max_chunk_size=1000, overlap=100)
    assert len(chunks) == 1
    assert chunks[0]["text"] == text
    assert chunks[0]["index"] == 0


def test_chunk_boundary_respected():
    para1 = "A" * 500
    para2 = "B" * 500
    text = f"{para1}\n\n{para2}"
    chunks = chunk_text(text, max_chunk_size=600, overlap=50)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["char_count"] <= 600 + 50


def test_overlap_included():
    para1 = "A" * 500
    para2 = "B" * 500
    text = f"{para1}\n\n{para2}"
    chunks = chunk_text(text, max_chunk_size=600, overlap=100)
    if len(chunks) > 1:
        assert len(chunks[1]["overlap_prefix"]) > 0


def test_exact_single_chunk():
    text = "X" * 100
    chunks = chunk_text(text, max_chunk_size=100, overlap=0)
    assert len(chunks) == 1


def test_multiple_paragraphs():
    text = "\n\n".join([f"Paragraph {i}." for i in range(10)])
    chunks = chunk_text(text, max_chunk_size=100, overlap=20)
    assert len(chunks) >= 2


def test_chunk_indexes_are_sequential():
    text = "\n\n".join([f"Para {i}." for i in range(20)])
    chunks = chunk_text(text, max_chunk_size=100, overlap=20)
    for i, c in enumerate(chunks):
        assert c["index"] == i
