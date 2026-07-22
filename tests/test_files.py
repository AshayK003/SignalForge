import io

import pytest
from io import BytesIO
from pathlib import Path

from app.storage.files import FileManager


@pytest.fixture
def file_manager(tmp_path):
    return FileManager(data_dir=str(tmp_path))


def test_save_upload(file_manager, tmp_path):
    content = b"sample upload content"
    upload = io.BytesIO(content)

    saved_path = file_manager.save_upload(upload, "test.txt")

    assert saved_path.exists()
    assert saved_path.parent == tmp_path / "raw"
    assert saved_path.read_bytes() == content


def test_save_upload_long_filename(file_manager):
    long_filename = "a" * 200 + ".txt"
    upload = io.BytesIO(b"long filename content")

    saved_path = file_manager.save_upload(upload, long_filename)

    assert saved_path.exists()
    assert saved_path.read_bytes() == b"long filename content"


def test_save_transcript(file_manager, tmp_path):
    source_id = 123
    text = "Transcript content"

    saved_path = file_manager.save_transcript(source_id, text)

    assert saved_path.exists()
    assert saved_path == tmp_path / "transcripts" / str(source_id) / "transcript.txt"
    assert saved_path.read_text(encoding="utf-8") == text


def test_save_transcript_empty_string(file_manager):
    saved_path = file_manager.save_transcript(1, "")

    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8") == ""


def test_save_summary(file_manager, tmp_path):
    source_id = 456
    text = "# Summary"

    saved_path = file_manager.save_summary(source_id, text)

    assert saved_path.exists()
    assert saved_path == tmp_path / "summaries" / str(source_id) / "summary.md"
    assert saved_path.read_text(encoding="utf-8") == text


def test_save_summary_custom_format(file_manager):
    saved_path = file_manager.save_summary(
        source_id=10,
        text="Custom summary",
        fmt="txt",
    )

    assert saved_path.exists()
    assert saved_path.suffix == ".txt"
    assert saved_path.read_text(encoding="utf-8") == "Custom summary"


def test_save_report_with_string_content(file_manager, tmp_path):
    filename = "report"
    content = "Report content"

    saved_path = file_manager.save_report(filename, content)

    assert saved_path.exists()
    assert saved_path == tmp_path / "reports" / "report.pdf"
    assert saved_path.read_text(encoding="utf-8") == content


def test_save_report_with_binary_content(file_manager):
    content = b"%PDF binary content"

    saved_path = file_manager.save_report("binary_report", content)

    assert saved_path.exists()
    assert saved_path.read_bytes() == content


def test_save_report_long_filename(file_manager):
    long_filename = "r" * 200

    saved_path = file_manager.save_report(long_filename, "content")

    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8") == "content"


def test_save_transcript_deeply_nested_source_id(file_manager):
    source_id = 999999999

    saved_path = file_manager.save_transcript(
        source_id,
        "deep source id transcript",
    )

    assert saved_path.exists()
    assert saved_path.parent.name == str(source_id)
    assert saved_path.read_text(encoding="utf-8") == "deep source id transcript"


def test_clean_temp(file_manager):
    temp_file = file_manager.temp / "temporary.txt"
    temp_file.write_text("temporary data", encoding="utf-8")

    assert temp_file.exists()

    file_manager.clean_temp()

    assert not temp_file.exists()


def test_clean_temp_keeps_directories(file_manager):
    nested_dir = file_manager.temp / "nested"
    nested_dir.mkdir()

    temp_file = nested_dir / "file.txt"
    temp_file.write_text("data", encoding="utf-8")

    file_manager.clean_temp()

    assert nested_dir.exists()
    assert temp_file.exists()
def test_file_manager_dirs(tmp_path: Path):
    fm = FileManager(str(tmp_path / "data"))
    assert fm.raw.is_dir()
    assert fm.transcripts.is_dir()
    assert fm.summaries.is_dir()
    assert fm.reports.is_dir()
    assert fm.temp.is_dir()


def test_save_upload_and_transcript(tmp_path: Path):
    fm = FileManager(str(tmp_path / "data"))
    path = fm.save_upload(BytesIO(b"hello"), "note.txt")
    assert path.exists()
    assert path.read_bytes() == b"hello"

    tpath = fm.save_transcript(42, "full text here", fmt="txt")
    assert tpath.exists()
    assert "full text" in tpath.read_text(encoding="utf-8")


def test_save_summary_report_and_clean_temp(tmp_path: Path):
    fm = FileManager(str(tmp_path / "data"))
    sp = fm.save_summary(7, "# summary", fmt="md")
    assert sp.suffix == ".md"
    assert sp.read_text(encoding="utf-8").startswith("#")

    rp = fm.save_report("weekly", "body", fmt="md")
    assert rp.exists()

    junk = fm.temp / "x.tmp"
    junk.write_text("tmp", encoding="utf-8")
    fm.clean_temp()
    assert not junk.exists()
