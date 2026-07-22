from pathlib import Path

import pytest

from app.extractors.text_extractor import extract_text


def test_extract_normal_text(tmp_path):
    file = tmp_path / "sample.txt"
    file.write_text("Hello\nWorld", encoding="utf-8")

    result = extract_text(file)

    assert result["text"] == "Hello\nWorld"
    assert result["file_path"] == str(file)
    assert result["line_count"] == 2
    assert result["file_size"] == file.stat().st_size


def test_extract_utf8_text(tmp_path):
    file = tmp_path / "utf8.txt"
    text = "தமிழ் 😀 café"

    file.write_text(text, encoding="utf-8")

    result = extract_text(file)

    assert result["text"] == text


def test_extract_empty_file(tmp_path):
    file = tmp_path / "empty.txt"
    file.write_text("", encoding="utf-8")

    result = extract_text(file)

    assert result["text"] == ""
    assert result["line_count"] == 1
    assert result["file_size"] == 0


def test_extract_binary_file_raises(tmp_path):
    file = tmp_path / "binary.bin"
    file.write_bytes(b"\xff\xfe\xfd")

    with pytest.raises(UnicodeDecodeError):
        extract_text(file)

