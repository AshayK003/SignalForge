from unittest.mock import MagicMock, patch

import pytest

from app.extractors.pdf_extractor import extract_text


def make_page(text):
    page = MagicMock()
    page.extract_text.return_value = text
    return page


@patch("app.extractors.pdf_extractor.PdfReader")
def test_extract_valid_pdf(mock_reader):
    mock_reader.return_value.pages = [
        make_page("Hello"),
        make_page("World"),
    ]

    result = extract_text("dummy.pdf", use_ocr_fallback=False)

    assert result["method"] == "direct"
    assert result["page_count"] == 2
    assert result["text"] == "Hello\n\nWorld"


@patch("app.extractors.pdf_extractor.PdfReader")
def test_extract_empty_pdf(mock_reader):
    mock_reader.return_value.pages = [
        make_page(""),
        make_page(""),
    ]

    result = extract_text("dummy.pdf", use_ocr_fallback=False)

    assert result["text"] == ""
    assert result["page_count"] == 2
    assert result["method"] == "ocr"


@patch("app.extractors.pdf_extractor._ocr_fallback")
@patch("app.extractors.pdf_extractor.PdfReader")
def test_extract_scanned_pdf_uses_ocr(mock_reader, mock_ocr):
    mock_reader.return_value.pages = [
        make_page(""),
    ]

    mock_ocr.return_value = {
        "text": "OCR TEXT",
        "pages": [],
        "page_count": 1,
        "method": "ocr",
    }

    result = extract_text("dummy.pdf")

    mock_ocr.assert_called_once()
    assert result["text"] == "OCR TEXT"


@patch("app.extractors.pdf_extractor.PdfReader")
def test_corrupted_pdf_raises(mock_reader):
    mock_reader.side_effect = Exception("Corrupted PDF")

    with pytest.raises(Exception):
        extract_text("broken.pdf")

