from io import BytesIO
from pathlib import Path

from app.storage.files import FileManager


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
