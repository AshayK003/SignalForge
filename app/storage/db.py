import json
import sqlite3
from datetime import datetime
from typing import Any

from database.schema import get_connection


class Database:
    def __init__(self, db_path: str | None = None):
        self._conn = get_connection(db_path)

    def close(self):
        self._conn.close()

    # --- Sources ---

    def insert_source(self, source_type: str, title: str = "", url: str | None = None,
                      file_path: str | None = None, file_size: int | None = None,
                      metadata: dict | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO sources (source_type, title, url, file_path, file_size, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (source_type, title, url, file_path, file_size, json.dumps(metadata or {})),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_source_status(self, source_id: int, status: str, error: str | None = None):
        self._conn.execute(
            "UPDATE sources SET status = ?, error = ? WHERE id = ?",
            (status, error, source_id),
        )
        self._conn.commit()

    def get_source(self, source_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None

    def list_sources(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM sources WHERE status = ? ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM sources ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def count_sources(self, status: str | None = None) -> int:
        if status:
            return self._conn.execute("SELECT COUNT(*) FROM sources WHERE status = ?", (status,)).fetchone()[0]
        return self._conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]

    # --- Tags ---

    def ensure_tag(self, name: str) -> int:
        existing = self._conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if existing:
            return existing[0]
        cur = self._conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        self._conn.commit()
        return cur.lastrowid

    def add_source_tag(self, source_id: int, tag_id: int):
        self._conn.execute("INSERT OR IGNORE INTO source_tags (source_id, tag_id) VALUES (?, ?)", (source_id, tag_id))
        self._conn.commit()

    def get_source_tags(self, source_id: int) -> list[str]:
        rows = self._conn.execute(
            "SELECT t.name FROM tags t JOIN source_tags st ON t.id = st.tag_id WHERE st.source_id = ?",
            (source_id,),
        ).fetchall()
        return [r[0] for r in rows]

    # --- Transcripts ---

    def insert_transcript(self, source_id: int, text: str, language: str = "unknown",
                          duration_seconds: float | None = None, segments: list | None = None,
                          model_used: str | None = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO transcripts (source_id, text, language, duration_seconds, segments, model_used) VALUES (?, ?, ?, ?, ?, ?)",
            (source_id, text, language, duration_seconds, json.dumps(segments or []), model_used),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_transcript(self, source_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM transcripts WHERE source_id = ? ORDER BY created_at DESC LIMIT 1",
            (source_id,),
        ).fetchone()
        return dict(row) if row else None

    # --- Summaries ---

    def insert_summary(self, source_id: int, level: str, summary_text: str,
                       insights: list | None = None, action_items: list | None = None,
                       key_quotes: list | None = None, themes: list | None = None,
                       technical_concepts: list | None = None, opportunities: list | None = None,
                       contradictions: list | None = None,
                       model_used: str | None = None, chunk_index: int | None = None,
                       parent_summary_id: int | None = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO summaries
               (source_id, level, parent_summary_id, summary_text, insights, action_items,
                key_quotes, themes, technical_concepts, opportunities, contradictions,
                model_used, chunk_index)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, level, parent_summary_id, summary_text,
             json.dumps(insights or []), json.dumps(action_items or []),
             json.dumps(key_quotes or []), json.dumps(themes or []),
             json.dumps(technical_concepts or []), json.dumps(opportunities or []),
             json.dumps(contradictions or []), model_used, chunk_index),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_source_summaries(self, source_id: int, level: str = "source") -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM summaries WHERE source_id = ? AND level = ? ORDER BY created_at DESC",
            (source_id, level),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_summaries_in_week(self, week_start: str, week_end: str) -> list[dict]:
        rows = self._conn.execute(
            """SELECT s.* FROM summaries s
               JOIN sources src ON s.source_id = src.id
               WHERE s.level = 'source'
               AND src.ingested_at >= ? AND src.ingested_at <= ?
               ORDER BY src.ingested_at""",
            (week_start, week_end),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Reports ---

    def insert_report(self, week_start: str, week_end: str, title: str = "",
                      executive_summary: str | None = None, source_count: int = 0,
                      local_pdf_path: str | None = None, local_md_path: str | None = None,
                      cloud_pdf_url: str | None = None, cloud_md_url: str | None = None,
                      metadata: dict | None = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO reports
               (week_start, week_end, title, executive_summary, source_count,
                local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (week_start, week_end, title, executive_summary, source_count,
             local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url,
             json.dumps(metadata or {})),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_report_cloud_urls(self, report_id: int, pdf_url: str | None = None, md_url: str | None = None):
        if pdf_url:
            self._conn.execute("UPDATE reports SET cloud_pdf_url = ? WHERE id = ?", (pdf_url, report_id))
        if md_url:
            self._conn.execute("UPDATE reports SET cloud_md_url = ? WHERE id = ?", (md_url, report_id))
        self._conn.commit()

    def list_reports(self, limit: int = 20, offset: int = 0) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM reports ORDER BY week_start DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_report(self, report_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else None

    def add_report_source(self, report_id: int, source_id: int):
        self._conn.execute("INSERT OR IGNORE INTO report_sources (report_id, source_id) VALUES (?, ?)",
                           (report_id, source_id))
        self._conn.commit()
