from pathlib import Path
from typing import Any

import pytesseract
from pypdf import PdfReader
from PIL import Image


def extract_text(pdf_path: str | Path, use_ocr_fallback: bool = True,
                 logger: Any = None) -> dict:
    pdf_path = Path(pdf_path)
    pages = []
    full_text_parts = []

    reader = PdfReader(str(pdf_path))

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text, "method": "direct"})
        full_text_parts.append(text)

    direct_text = "\n\n".join(full_text_parts).strip()

    if not direct_text and use_ocr_fallback:
        if logger:
            logger("No text extracted directly, falling back to OCR...")
        return _ocr_fallback(pdf_path, logger)

    return {
        "text": direct_text,
        "pages": pages,
        "page_count": len(pages),
        "method": "direct" if direct_text else "ocr",
    }


def _ocr_fallback(pdf_path: Path, logger: Any = None) -> dict:
    images = _pdf_to_images(pdf_path)
    pages = []
    full_text_parts = []

    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        pages.append({"page": i + 1, "text": text, "method": "ocr"})
        full_text_parts.append(text)

    return {
        "text": "\n\n".join(full_text_parts).strip(),
        "pages": pages,
        "page_count": len(pages),
        "method": "ocr",
    }


def _pdf_to_images(pdf_path: Path) -> list[Image.Image]:
    try:
        from pdf2image import convert_from_path
        return convert_from_path(str(pdf_path), dpi=300)
    except ImportError:
        raise RuntimeError(
            "OCR fallback requires 'pdf2image' (pip install pdf2image) "
            "and poppler on your system PATH."
        )
