import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


def file_hash(path: str | Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(text: str, max_len: int = 80) -> str:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in text)
    return safe.strip()[:max_len]


def slugify(text: str) -> str:
    return safe_filename(text).lower().replace(" ", "_")


def week_boundary(dt: datetime | None = None) -> tuple[str, str]:
    dt = dt or datetime.now()
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_json_field(value: str | list | dict) -> list | dict:
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []
