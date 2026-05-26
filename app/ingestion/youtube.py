import json
import subprocess
from pathlib import Path
from typing import Any

from app.utils.helpers import safe_filename


def download_audio(url: str, output_dir: str | Path, logger: Any = None) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        "--print", "after_move:%(title)s|%(id)s|%(duration)s|%(uploader)s|%(upload_date)s|%(webpage_url)s",
        url,
    ]

    log = logger.debug if logger else print
    log(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")

    parts = result.stdout.strip().split("|")
    title = parts[0] if len(parts) > 0 else "Unknown"
    video_id = parts[1] if len(parts) > 1 else "unknown"
    duration = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    uploader = parts[3] if len(parts) > 3 else ""
    upload_date = parts[4] if len(parts) > 4 else ""
    webpage_url = parts[5] if len(parts) > 5 else url

    audio_files = list(output_dir.glob(f"{video_id}.*"))
    audio_path = str(audio_files[0]) if audio_files else ""

    metadata = {
        "title": title,
        "video_id": video_id,
        "duration_seconds": duration,
        "uploader": uploader,
        "upload_date": upload_date,
        "source_url": webpage_url,
    }
    log(f"Downloaded: {title} ({duration}s)")

    return {
        "title": title,
        "url": webpage_url,
        "audio_path": audio_path,
        "duration_seconds": duration,
        "metadata": metadata,
    }


def extract_metadata(url: str) -> dict:
    cmd = ["yt-dlp", "--dump-json", url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata extraction failed: {result.stderr.strip()}")

    return json.loads(result.stdout)
