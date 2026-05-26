from pathlib import Path
from typing import Any

from pypdf import PdfReader
from PIL import Image

from app.utils.deps import ensure_local_paths


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
    ensure_local_paths()
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
