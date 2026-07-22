from app.storage.db import Database


def test_source_crud_and_tags(db):
    # conftest provides initialized sqlite schema via get_connection path
    d = Database()
    sid = d.insert_source("web", title="Hello", url="https://ex.test/a")
    assert isinstance(sid, int) and sid > 0

    row = d.get_source(sid)
    assert row is not None
    assert row["title"] == "Hello"

    d.update_source_status(sid, "done")
    row2 = d.get_source(sid)
    assert row2["status"] == "done"

    by_url = d.get_source_by_url("https://ex.test/a")
    assert by_url is not None
    assert by_url["id"] == sid

    listed = d.list_sources(limit=10)
    assert any(r["id"] == sid for r in listed)
    assert d.count_sources() >= 1

    tid = d.ensure_tag("alpha")
    d.add_source_tag(sid, tid)
    tags = d.get_source_tags(sid)
    assert "alpha" in tags
    # ensure_tag is idempotent
    tid2 = d.ensure_tag("alpha")
    assert tid2 == tid
