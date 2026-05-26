import os
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from PIL import Image

_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_POPPLER_BIN = (
    r"C:\Users\Ashay\AppData\Local\Microsoft\WinGet\Packages"
    r"\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\poppler-25.07.0\Library\bin"
)


def _ensure_deps():
    for p in [_POPPLER_BIN, os.path.dirname(_TESSERACT_CMD)]:
        if p not in os.environ.get("PATH", "") and os.path.isdir(p):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    if not os.path.exists(_TESSERACT_CMD):
        raise RuntimeError(
            "Tesseract OCR engine not found at expected path. "
            "This PDF contains no extractable text (likely image-based). "
            "Install Tesseract from: "
            "https://github.com/UB-Mannheim/tesseract/releases"
        )


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
            logger.info("No text extracted directly, falling back to OCR...")
        return _ocr_fallback(pdf_path, logger)

    return {
        "text": direct_text,
        "pages": pages,
        "page_count": len(pages),
        "method": "direct" if direct_text else "ocr",
    }


def _ocr_fallback(pdf_path: Path, logger: Any = None) -> dict:
    _ensure_deps()
    import pytesseract

    images = _pdf_to_images(pdf_path)
    pages = []
    full_text_parts = []

    for i, img in enumerate(images):
        if logger:
            logger.info(f"OCR processing page {i + 1}/{len(images)}...")
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
    except ImportError:
        raise RuntimeError(
            "OCR requires 'pdf2image'. Install with: pip install pdf2image"
        )
    try:
        return convert_from_path(str(pdf_path), dpi=300)
    except Exception as e:
        msg = str(e).lower()
        if "pdftoppm" in msg or "poppler" in msg or "not found" in msg:
            raise RuntimeError(
                "Poppler is not on your PATH. "
                "Install it with: winget install oschwartz10612.Poppler"
            ) from e
        raise RuntimeError(f"PDF to image conversion failed: {e}") from e
