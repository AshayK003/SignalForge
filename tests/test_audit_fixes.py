"""Regression tests for the Sep 2026 audit fixes (P0/P1/P2).

Each test pins one verified bug so it can never silently return.
"""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import bot
from app.ingestion.youtube import (
    MAX_VIDEO_SECONDS,
    download_audio,
    find_youtube_url,
    is_youtube_url,
)
from app.reports.generator import ReportGenerator
from app.reports.pdf_gen import generate_pdf, strip_markdown
from app.summarization.chunker import _word_overlap, chunk_text

VALID_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    "https://www.youtube.com/live/dQw4w9WgXcQ",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
]

BAD_URLS = [
    "https://vimeo.com/123456",
    "https://youtube.com/watch?v=short",
    "https://youtube.com/",
    "https://youtu.be/",
    "https://evil-youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
    "",
    None,
    "not a url",
    "http://169.254.169.254/latest/meta-data",
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_youtube_allowlist_accepts(url):
    assert is_youtube_url(url)


@pytest.mark.parametrize("url", BAD_URLS)
def test_youtube_allowlist_rejects(url):
    assert not is_youtube_url(url)


def test_find_youtube_url_embedded():
    text = "hey check this https://youtu.be/dQw4w9WgXcQ looks interesting"
    assert find_youtube_url(text) == "https://youtu.be/dQw4w9WgXcQ"
    assert find_youtube_url("no links here, just youtube.com mentioned") is None
    assert find_youtube_url("see log: youtube.com/error failed") is None


def test_download_rejects_livestream_and_marathon(monkeypatch):
    import app.ingestion.youtube as yt

    monkeypatch.setattr(yt, "extract_metadata",
                        lambda url: {"id": "x", "title": "t", "duration": None})
    with pytest.raises(RuntimeError):
        download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "/tmp")
    monkeypatch.setattr(yt, "extract_metadata",
                        lambda url: {"id": "x", "title": "t",
                                     "duration": MAX_VIDEO_SECONDS + 1})
    with pytest.raises(RuntimeError):
        download_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "/tmp")


def test_auth_fail_closed(monkeypatch):
    monkeypatch.setattr(bot, "ALLOWED_USERS", set())
    monkeypatch.setenv("ALLOW_OPEN_BOT", "")
    upd = SimpleNamespace(effective_user=SimpleNamespace(id=123))
    assert not bot._is_authorized(upd)
    monkeypatch.setenv("ALLOW_OPEN_BOT", "1")
    assert bot._is_authorized(upd)
    monkeypatch.setattr(bot, "ALLOWED_USERS", {"123"})
    monkeypatch.setenv("ALLOW_OPEN_BOT", "")
    assert bot._is_authorized(upd)
    upd2 = SimpleNamespace(effective_user=SimpleNamespace(id=999))
    assert not bot._is_authorized(upd2)


def test_word_overlap_no_midword_cut():
    prev = "the quick brown fox jumps"
    assert _word_overlap(prev, 10) == "fox jumps"
    assert _word_overlap(prev, 5) == "jumps"
    assert _word_overlap(prev, 4) == "umps"  # nothing fits: char fallback
    assert _word_overlap("", 10) == ""
    assert _word_overlap(prev, 0) == ""


def test_large_paragraph_chunks_keep_prefix():
    para = " ".join(f"Sentence number {i} here." for i in range(40))
    chunks = chunk_text(para, max_chunk_size=200, overlap=30)
    assert len(chunks) > 1
    assert all(len(c["overlap_prefix"]) > 0 for c in chunks[1:])


def test_chunk_budget_counts_separators():
    paras = ["word " * 30, "word " * 30, "word " * 30]
    text = "\n\n".join(paras)
    chunks = chunk_text(text, max_chunk_size=200, overlap=20)
    assert all(c["char_count"] <= 200 for c in chunks)


def test_why_it_matters_list_normalized(db):
    sid = db.insert_source("manual", title="t")
    db.insert_summary(sid, level="source", summary_text="s",
                      why_it_matters=["a", "b"])
    rows = db.get_source_summaries(sid)
    assert rows[0]["why_it_matters"] == "a; b"


def test_strip_markdown_none():
    assert strip_markdown(None) == ""


def _ensure_test_font(monkeypatch):
    """Point the PDF renderer at DejaVu on fontless CI runners.

    Keeps render tests hermetic: same code path, only the font asset
    differs. Skips only when no usable TTF exists at all.
    """
    import os

    import app.reports.pdf_gen as pg

    base = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
    cands = {
        "regular": base + ".ttf",
        "bold": base + "-Bold.ttf",
        "italic": base + "-Oblique.ttf",
        "bold_italic": base + "-BoldOblique.ttf",
    }
    if all(os.path.exists(p) for p in cands.values()):
        monkeypatch.setitem(pg._FONTS, "ci-dejavu", cands)
        monkeypatch.setattr(pg, "_find_unicode_font", lambda: "ci-dejavu")
        return
    try:
        pg._find_unicode_font()
    except RuntimeError:
        pytest.skip("no usable Unicode font on this machine")


def test_generate_pdf_returns_bytes(monkeypatch):
    _ensure_test_font(monkeypatch)
    data = generate_pdf(title="t", week_start="2026-08-31",
                        week_end="2026-09-06", executive_summary="hello",
                        source_count=0, insights=[], action_items=[],
                        quotes=[], themes=[], opportunities=[],
                        contradictions=[])
    assert isinstance(data, bytes)
    assert data.startswith(b"%PDF")


def _mock_report_deps():
    llm = Mock()
    llm.chat.return_value = json.dumps({
        "executive_summary": "exec",
        "key_developments": ["k"],
        "cross_source_connections": [],
        "recommended_actions": ["r"],
        "signals_to_monitor": ["s"],
    })
    prompts = Mock()
    prompts.render.return_value = "prompt"
    files = Mock()
    files.save_report.side_effect = ["/tmp/r.md", "/tmp/r.pdf"]
    return files, llm, prompts


def test_weekly_end_of_day_includes_sunday(db, monkeypatch):
    _ensure_test_font(monkeypatch)
    sid = db.insert_source("manual", title="sunday")
    db.insert_summary(sid, level="source", summary_text="sunday work")
    files, llm, prompts = _mock_report_deps()
    gen = ReportGenerator(db, files, llm, prompts)
    # End bound far future date-only: pre-fix string compare dropped today.
    res = gen.generate_weekly(week_start="2000-01-01", week_end="2100-01-01")
    assert res["status"] == "created"
    assert db.get_report(res["report_id"])["id"] == res["report_id"]


def test_weekly_empty_window_skips(db):
    files, llm, prompts = _mock_report_deps()
    gen = ReportGenerator(db, files, llm, prompts)
    res = gen.generate_weekly(week_start="2000-01-01", week_end="2000-01-02")
    assert res["status"] == "skipped"
    llm.chat.assert_not_called()
