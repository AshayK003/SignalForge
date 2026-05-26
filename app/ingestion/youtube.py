import json
import re
import subprocess
from pathlib import Path
from typing import Any

import os

from app.utils.deps import DENO_PATH, FFMPEG_PATH, extended_env

_COOKIES_FILE = Path(os.getenv("SIGNALFORGE_DATA_DIR", "./data")) / "cookies.txt"

_YTDLP_BASE = [
    "yt-dlp",
    "--remote-components", "ejs:github",
    "--extractor-args", "youtube:skip=web_safari",
]


def _build_cmd(*args: str) -> list[str]:
    cmd = _YTDLP_BASE + list(args)
    if _COOKIES_FILE.exists():
        cmd += ["--cookies", str(_COOKIES_FILE)]
    return cmd


def download_audio(url: str, output_dir: str | Path, logger: Any = None,
                   ffmpeg_path: str | None = None) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # get metadata first (quick, no download)
    info = extract_metadata(url)
    video_id = info.get("id", "unknown")
    title = info.get("title", "Unknown")
    duration = info.get("duration", 0)
    webpage_url = info.get("webpage_url", url)
    uploader = info.get("uploader", "")
    upload_date = info.get("upload_date", "")

    output_template = str(output_dir / "%(id)s.%(ext)s")

    cmd = _build_cmd(
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        "--ffmpeg-location", ffmpeg_path or FFMPEG_PATH,
        url,
    )

    log = logger.debug if logger else print
    log(f"Downloading: {title} ({duration}s)")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=extended_env())

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed: {result.stderr.strip()}")

    # find audio file by most recently modified mp3
    audio_files = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
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
    cmd = _build_cmd("--dump-json", url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=extended_env())

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata extraction failed: {result.stderr.strip()}")

    return json.loads(result.stdout)


def get_captions(url: str, output_dir: str | Path | None = None,
                 logger: Any = None) -> dict | None:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

    log = logger.debug if logger else print

    video_id = _extract_video_id(url)
    if not video_id:
        log(f"Could not extract video ID from URL: {url}")
        return None

    log(f"Fetching captions for video {video_id}...")

    try:
        api = YouTubeTranscriptApi()
        caption_data = api.fetch(video_id, languages=["en"])

        segments = [
            {"start": round(s["start"], 2), "end": round(s["start"] + s["duration"], 2), "text": s["text"].strip()}
            for s in caption_data
        ]
        text = " ".join(s["text"] for s in segments)
        duration = round(segments[-1]["end"]) if segments else 0

        log(f"Captions fetched: {len(text)} chars, {len(segments)} segments")

        return {
            "text": text,
            "title": "",
            "url": url,
            "video_id": video_id,
            "duration_seconds": duration,
            "uploader": "",
            "method": "youtube-transcript-api",
        }

    except Exception as e:
        log(f"No captions available: {e}")
        return None


def _extract_video_id(url: str) -> str | None:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None
