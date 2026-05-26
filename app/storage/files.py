import shutil
from pathlib import Path
from typing import BinaryIO

from app.utils.helpers import ensure_dir, safe_filename


class FileManager:
    def __init__(self, data_dir: str = "./data"):
        self.base = Path(data_dir)
        self.raw = ensure_dir(self.base / "raw")
        self.transcripts = ensure_dir(self.base / "transcripts")
        self.summaries = ensure_dir(self.base / "summaries")
        self.markdown = ensure_dir(self.base / "markdown")
        self.reports = ensure_dir(self.base / "reports")
        self.temp = ensure_dir(self.base / "temp")

    def save_upload(self, file: BinaryIO, filename: str) -> Path:
        dest = self.raw / safe_filename(filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file, f)
        return dest

    def save_transcript(self, source_id: int, text: str, fmt: str = "txt") -> Path:
        sub = ensure_dir(self.transcripts / str(source_id))
        path = sub / f"transcript.{fmt}"
        path.write_text(text, encoding="utf-8")
        return path

    def save_summary(self, source_id: int, text: str, fmt: str = "md") -> Path:
        sub = ensure_dir(self.summaries / str(source_id))
        path = sub / f"summary.{fmt}"
        path.write_text(text, encoding="utf-8")
        return path

    def save_report(self, filename: str, content: str | bytes, fmt: str = "pdf") -> Path:
        path = self.reports / f"{safe_filename(filename)}.{fmt}"
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
        return path

    def clean_temp(self):
        for f in self.temp.iterdir():
            if f.is_file():
                f.unlink()

    def get_raw_path(self, filename: str) -> Path | None:
        path = self.raw / filename
        return path if path.exists() else None
