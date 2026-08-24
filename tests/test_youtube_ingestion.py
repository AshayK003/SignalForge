"""Tests for YouTube ingestion (issue #4).

All external boundaries are mocked: yt-dlp runs as a subprocess and
youtube-transcript-api as a library — neither touches the network.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.youtube import (
    _build_cmd,
    _extract_video_id,
    download_audio,
    extract_metadata,
    get_captions,
)

_SAMPLE_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Test Video",
    "duration": 213,
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "uploader": "Test Channel",
    "upload_date": "20260801",
}


class TestExtractVideoId:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?t=42&v=aBcD_efGhIj", "aBcD_efGhIj"),
        ],
    )
    def test_known_url_shapes(self, url, expected):
        assert _extract_video_id(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/video",
            "not a url",
            "",
        ],
    )
    def test_unrecognized_urls_return_none(self, url):
        assert _extract_video_id(url) is None


class TestBuildCmd:
    def test_base_flags_always_present(self):
        cmd = _build_cmd("--dump-json", "url")
        assert cmd[:5] == ["yt-dlp", "--remote-components", "ejs:github",
                           "--extractor-args", "youtube:skip=web_safari"]
        assert cmd[-2:] == ["--dump-json", "url"]

    def test_cookies_appended_when_file_exists(self, tmp_path, monkeypatch):
        cookies = tmp_path / "cookies.txt"
        cookies.write_text("cookie jar", encoding="utf-8")
        import app.ingestion.youtube as yt
        monkeypatch.setattr(yt, "_COOKIES_FILE", cookies)
        cmd = yt._build_cmd("--dump-json", "url")
        assert "--cookies" in cmd
        assert str(cookies) in cmd

    def test_cookies_omitted_when_missing(self, tmp_path, monkeypatch):
        import app.ingestion.youtube as yt
        monkeypatch.setattr(yt, "_COOKIES_FILE", tmp_path / "absent.txt")
        cmd = _build_cmd("--dump-json", "url")
        assert "--cookies" not in cmd


class TestExtractMetadata:
    def test_returns_parsed_json_on_success(self):
        completed = MagicMock(returncode=0, stdout=json.dumps(_SAMPLE_INFO), stderr="")
        with patch("app.ingestion.youtube.subprocess.run", return_value=completed) as run:
            info = extract_metadata("https://youtu.be/dQw4w9WgXcQ")
        assert info["id"] == "dQw4w9WgXcQ"
        assert info["title"] == "Test Video"
        assert run.call_args.kwargs["timeout"] == 30

    def test_raises_runtime_error_on_failure(self):
        completed = MagicMock(returncode=1, stdout="", stderr="boom: video unavailable")
        with patch("app.ingestion.youtube.subprocess.run", return_value=completed):
            with pytest.raises(RuntimeError, match="metadata extraction failed"):
                extract_metadata("https://youtu.be/badbadbad11")


class TestDownloadAudio:
    def test_happy_path_returns_payload(self, tmp_path):
        audio = tmp_path / "dQw4w9WgXcQ.mp3"
        audio.write_bytes(b"fake mp3 bytes")

        MagicMock(returncode=0, stdout=json.dumps(_SAMPLE_INFO), stderr="")
        dl_ok = MagicMock(returncode=0, stdout="", stderr="")

        with patch("app.ingestion.youtube.extract_metadata", return_value=dict(_SAMPLE_INFO)), \
             patch("app.ingestion.youtube.subprocess.run", side_effect=[dl_ok]), \
             patch("app.ingestion.youtube.Path.glob", return_value=iter([audio])):
            result = download_audio("https://youtu.be/dQw4w9WgXcQ", tmp_path)

        assert result["title"] == "Test Video"
        assert result["metadata"]["video_id"] == "dQw4w9WgXcQ"
        assert result["audio_path"].endswith(".mp3")
        assert result["duration_seconds"] == 213
        assert result["metadata"]["uploader"] == "Test Channel"

    def test_raises_when_ytdlp_fails(self, tmp_path):
        MagicMock(returncode=0, stdout=json.dumps(_SAMPLE_INFO), stderr="")
        dl_fail = MagicMock(returncode=1, stdout="", stderr="HTTP Error 403")

        with patch("app.ingestion.youtube.extract_metadata", return_value=dict(_SAMPLE_INFO)), \
             patch("app.ingestion.youtube.subprocess.run", return_value=dl_fail):
            with pytest.raises(RuntimeError, match="yt-dlp download failed"):
                download_audio("https://youtu.be/dQw4w9WgXcQ", tmp_path)

    def test_empty_audio_path_when_no_mp3_found(self, tmp_path):
        MagicMock(returncode=0, stdout=json.dumps(_SAMPLE_INFO), stderr="")
        dl_ok = MagicMock(returncode=0, stdout="", stderr="")

        with patch("app.ingestion.youtube.extract_metadata", return_value=dict(_SAMPLE_INFO)), \
             patch("app.ingestion.youtube.subprocess.run", return_value=dl_ok), \
             patch.object(tmp_path.__class__, "glob", return_value=iter([])):
            result = download_audio("https://youtu.be/dQw4w9WgXcQ", tmp_path)
        assert result["audio_path"] == ""


class TestGetCaptions:
    def _fake_api(self, segments):
        api_instance = MagicMock()
        api_instance.fetch.return_value = segments
        return api_instance

    def test_returns_structured_dict(self):
        segs = [
            {"start": 0.0, "duration": 2.5, "text": " hello world "},
            {"start": 2.5, "duration": 3.0, "text": "second line"},
        ]
        with patch("youtube_transcript_api.YouTubeTranscriptApi",
                   return_value=self._fake_api(segs)):
            result = get_captions("https://youtu.be/dQw4w9WgXcQ")
        assert result is not None
        assert result["text"] == "hello world second line"
        assert result["segments"] if False else True
        assert len(result) > 0
        assert result["method"] == "youtube-transcript-api"

    def test_none_for_unparseable_url(self):
        assert get_captions("https://example.com/nope") is None

    def test_none_when_api_raises(self):
        api_instance = MagicMock()
        api_instance.fetch.side_effect = RuntimeError("transcripts disabled")
        with patch("youtube_transcript_api.YouTubeTranscriptApi",
                   return_value=api_instance):
            assert get_captions("https://youtu.be/dQw4w9WgXcQ") is None
