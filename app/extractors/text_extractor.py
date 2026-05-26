from pathlib import Path


def extract_text(file_path: str | Path) -> dict:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    return {
        "text": text,
        "file_path": str(path),
        "file_size": path.stat().st_size,
        "line_count": text.count("\n") + 1,
    }
