import pytest
from database.schema import init_db, get_connection


def test_all_tables_created(tmp_db_path):
    conn = init_db(tmp_db_path)
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    assert "sources" in tables
    assert "transcripts" in tables
    assert "summaries" in tables
    assert "reports" in tables
    assert "tags" in tables
    assert "source_tags" in tables
    assert "report_sources" in tables
    conn.close()


def test_source_insert_and_retrieve(tmp_db_path):
    conn = init_db(tmp_db_path)
    conn.execute(
        "INSERT INTO sources (source_type, title, url) VALUES (?, ?, ?)",
        ("youtube", "Test Video", "https://youtube.com/watch?v=test"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sources WHERE id = 1").fetchone()
    assert row["title"] == "Test Video"
    assert row["source_type"] == "youtube"
    assert row["status"] == "pending"
    conn.close()


def test_source_status_constraint(tmp_db_path):
    conn = init_db(tmp_db_path)
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO sources (source_type, title, status) VALUES (?, ?, ?)",
            ("pdf", "Bad Status", "invalid_status"),
        )
    conn.close()


def test_foreign_key_cascade(tmp_db_path):
    conn = init_db(tmp_db_path)
    conn.execute("INSERT INTO sources (source_type, title) VALUES (?, ?)", ("text", "Test"))
    conn.commit()
    conn.execute("INSERT INTO transcripts (source_id, text) VALUES (?, ?)", (1, "Transcript text"))
    conn.commit()
    conn.execute("DELETE FROM sources WHERE id = 1")
    conn.commit()
    rows = conn.execute("SELECT * FROM transcripts WHERE source_id = 1").fetchall()
    assert len(rows) == 0
    conn.close()


def test_report_insert(tmp_db_path):
    conn = init_db(tmp_db_path)
    conn.execute(
        "INSERT INTO reports (week_start, week_end, title) VALUES (?, ?, ?)",
        ("2026-01-01", "2026-01-07", "Weekly Report"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reports WHERE id = 1").fetchone()
    assert row["title"] == "Weekly Report"
    conn.close()
