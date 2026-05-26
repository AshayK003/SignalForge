import mimetypes
from pathlib import Path
from typing import BinaryIO


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "text",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".flac": "audio",
    ".wma": "audio",
}


def classify_file(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext, "unknown")


def save_uploaded_file(file: BinaryIO, filename: str, dest_dir: str | Path) -> dict:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    content = file.read()
    dest.write_bytes(content)

    return {
        "file_path": str(dest),
        "file_size": len(content),
        "file_type": classify_file(filename),
        "filename": filename,
    }
