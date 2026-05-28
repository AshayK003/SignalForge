import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def safe_filename(text: str, max_len: int = 80) -> str:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in text)
    return safe.strip()[:max_len]


def week_boundary(dt: datetime | None = None) -> tuple[str, str]:
    dt = dt or datetime.now(timezone.utc)
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def parse_json_field(value: str | list | dict) -> list | dict:
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []
