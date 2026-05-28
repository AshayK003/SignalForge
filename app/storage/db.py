import json
import sqlite3
import time

from database.schema import get_connection

_RETRIES = 5
_RETRY_DELAY = 0.5


class Database:
    @staticmethod
    def _conn():
        return get_connection()

    @staticmethod
    def _retry(fn):
        for attempt in range(_RETRIES):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < _RETRIES - 1:
                    time.sleep(_RETRY_DELAY * (2 ** attempt))
                    continue
                raise

    # --- Sources ---

    def insert_source(self, source_type: str, title: str = "", url: str | None = None,
                      file_path: str | None = None, file_size: int | None = None,
                      metadata: dict | None = None) -> int:
        return self._retry(lambda: self._insert_source(source_type, title, url, file_path, file_size, metadata))

    def _insert_source(self, source_type, title, url, file_path, file_size, metadata):
        c = self._conn()
        try:
            cur = c.execute(
                "INSERT INTO sources (source_type, title, url, file_path, file_size, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (source_type, title, url, file_path, file_size, json.dumps(metadata or {})),
            )
            c.commit()
            return cur.lastrowid
        finally:
            c.close()

    def update_source_status(self, source_id: int, status: str, error: str | None = None):
        self._retry(lambda: self._update_source_status(source_id, status, error))

    def _update_source_status(self, source_id, status, error):
        c = self._conn()
        try:
            c.execute("UPDATE sources SET status = ?, error = ? WHERE id = ?", (status, error, source_id))
            c.commit()
        finally:
            c.close()

    def get_source(self, source_id: int) -> dict | None:
        return self._retry(lambda: self._get_source(source_id))

    def _get_source(self, source_id):
        c = self._conn()
        try:
            row = c.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            return dict(row) if row else None
        finally:
            c.close()

    def get_source_by_url(self, url: str) -> dict | None:
        return self._retry(lambda: self._get_source_by_url(url))

    def _get_source_by_url(self, url):
        c = self._conn()
        try:
            row = c.execute(
                "SELECT * FROM sources WHERE url = ? ORDER BY ingested_at DESC LIMIT 1", (url,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            c.close()

    def list_sources(self, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        return self._retry(lambda: self._list_sources(status, limit, offset))

    def _list_sources(self, status, limit, offset):
        c = self._conn()
        try:
            if status:
                rows = c.execute(
                    "SELECT * FROM sources WHERE status = ? ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM sources ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    def count_sources(self, status: str | None = None) -> int:
        return self._retry(lambda: self._count_sources(status))

    def _count_sources(self, status):
        c = self._conn()
        try:
            if status:
                count = c.execute("SELECT COUNT(*) FROM sources WHERE status = ?", (status,)).fetchone()[0]
            else:
                count = c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count
        finally:
            c.close()

    # --- Tags ---

    def ensure_tag(self, name: str) -> int:
        return self._retry(lambda: self._ensure_tag(name))

    def _ensure_tag(self, name):
        c = self._conn()
        try:
            existing = c.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
            if existing:
                return existing[0]
            cur = c.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            c.commit()
            return cur.lastrowid
        finally:
            c.close()

    def add_source_tag(self, source_id: int, tag_id: int):
        self._retry(lambda: self._add_source_tag(source_id, tag_id))

    def _add_source_tag(self, source_id, tag_id):
        c = self._conn()
        try:
            c.execute("INSERT OR IGNORE INTO source_tags (source_id, tag_id) VALUES (?, ?)", (source_id, tag_id))
            c.commit()
        finally:
            c.close()

    def get_source_tags(self, source_id: int) -> list[str]:
        return self._retry(lambda: self._get_source_tags(source_id))

    def _get_source_tags(self, source_id):
        c = self._conn()
        try:
            rows = c.execute(
                "SELECT t.name FROM tags t JOIN source_tags st ON t.id = st.tag_id WHERE st.source_id = ?",
                (source_id,),
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            c.close()

    # --- Transcripts ---

    def insert_transcript(self, source_id: int, text: str, language: str = "unknown",
                          duration_seconds: float | None = None, segments: list | None = None,
                          model_used: str | None = None) -> int:
        return self._retry(lambda: self._insert_transcript(source_id, text, language, duration_seconds, segments, model_used))

    def _insert_transcript(self, source_id, text, language, duration_seconds, segments, model_used):
        c = self._conn()
        try:
            cur = c.execute(
                "INSERT INTO transcripts (source_id, text, language, duration_seconds, segments, model_used) VALUES (?, ?, ?, ?, ?, ?)",
                (source_id, text, language, duration_seconds, json.dumps(segments or []), model_used),
            )
            c.commit()
            return cur.lastrowid
        finally:
            c.close()

    def get_transcript(self, source_id: int) -> dict | None:
        return self._retry(lambda: self._get_transcript(source_id))

    def _get_transcript(self, source_id):
        c = self._conn()
        try:
            row = c.execute(
                "SELECT * FROM transcripts WHERE source_id = ? ORDER BY created_at DESC LIMIT 1",
                (source_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            c.close()

    # --- Summaries ---

    def insert_summary(self, source_id: int, level: str, summary_text: str,
                       core_ideas: list | None = None, insights: list | None = None,
                       action_items: list | None = None, key_quotes: list | None = None,
                       themes: list | None = None, technical_concepts: list | None = None,
                       opportunities: list | None = None, contradictions: list | None = None,
                       why_it_matters: str = "", open_questions: list | None = None,
                       model_used: str | None = None, chunk_index: int | None = None,
                       parent_summary_id: int | None = None) -> int:
        return self._retry(lambda: self._insert_summary(
            source_id, level, summary_text, core_ideas, insights, action_items,
            key_quotes, themes, technical_concepts, opportunities, contradictions,
            why_it_matters, open_questions, model_used, chunk_index, parent_summary_id))

    def _insert_summary(self, source_id, level, summary_text, core_ideas,
                        insights, action_items, key_quotes, themes,
                        technical_concepts, opportunities, contradictions,
                        why_it_matters, open_questions, model_used, chunk_index,
                        parent_summary_id=None):
        c = self._conn()
        try:
            cur = c.execute(
                """INSERT INTO summaries
                   (source_id, level, parent_summary_id, summary_text, core_ideas, insights, action_items,
                    key_quotes, themes, technical_concepts, opportunities, contradictions,
                    why_it_matters, open_questions, model_used, chunk_index)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source_id, level, parent_summary_id, summary_text,
             json.dumps(core_ideas or []), json.dumps(insights or []),
             json.dumps(action_items or []), json.dumps(key_quotes or []),
             json.dumps(themes or []), json.dumps(technical_concepts or []),
             json.dumps(opportunities or []), json.dumps(contradictions or []),
             why_it_matters, json.dumps(open_questions or []), model_used, chunk_index),
        )
            c.commit()
            return cur.lastrowid
        finally:
            c.close()

    def get_source_summary_count(self, source_id: int) -> int:
        return self._retry(lambda: self._get_source_summary_count(source_id))

    def _get_source_summary_count(self, source_id):
        c = self._conn()
        try:
            count = c.execute("SELECT COUNT(*) FROM summaries WHERE source_id = ?", (source_id,)).fetchone()[0]
            return count
        finally:
            c.close()

    def get_source_summaries(self, source_id: int, level: str = "source") -> list[dict]:
        return self._retry(lambda: self._get_source_summaries(source_id, level))

    def _get_source_summaries(self, source_id, level):
        c = self._conn()
        try:
            rows = c.execute(
                "SELECT * FROM summaries WHERE source_id = ? AND level = ? ORDER BY created_at DESC",
                (source_id, level),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    def get_summaries_in_week(self, week_start: str, week_end: str) -> list[dict]:
        return self._retry(lambda: self._get_summaries_in_week(week_start, week_end))

    def _get_summaries_in_week(self, week_start, week_end):
        c = self._conn()
        try:
            rows = c.execute(
                """SELECT s.* FROM summaries s
                   JOIN sources src ON s.source_id = src.id
                   WHERE s.level = 'source'
                   AND src.ingested_at >= ? AND src.ingested_at <= ?
                   ORDER BY src.ingested_at""",
                (week_start, week_end),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    # --- Reports ---

    def insert_report(self, week_start: str, week_end: str, title: str = "",
                      executive_summary: str | None = None, source_count: int = 0,
                      local_pdf_path: str | None = None, local_md_path: str | None = None,
                      cloud_pdf_url: str | None = None, cloud_md_url: str | None = None,
                      metadata: dict | None = None) -> int:
        return self._retry(lambda: self._insert_report(
            week_start, week_end, title, executive_summary, source_count,
            local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url, metadata))

    def _insert_report(self, week_start, week_end, title, executive_summary, source_count,
                       local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url, metadata):
        c = self._conn()
        try:
            cur = c.execute(
                """INSERT INTO reports
                   (week_start, week_end, title, executive_summary, source_count,
                    local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (week_start, week_end, title, executive_summary, source_count,
                 local_pdf_path, local_md_path, cloud_pdf_url, cloud_md_url,
                 json.dumps(metadata or {})),
            )
            c.commit()
            return cur.lastrowid
        finally:
            c.close()

    def list_reports(self, limit: int = 20, offset: int = 0) -> list[dict]:
        return self._retry(lambda: self._list_reports(limit, offset))

    def _list_reports(self, limit, offset):
        c = self._conn()
        try:
            rows = c.execute(
                "SELECT * FROM reports ORDER BY week_start DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    def get_report(self, report_id: int) -> dict | None:
        return self._retry(lambda: self._get_report(report_id))

    def _get_report(self, report_id):
        c = self._conn()
        try:
            row = c.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            return dict(row) if row else None
        finally:
            c.close()

    # --- Admin ---

    def clear_all_tables(self):
        self._retry(lambda: self._clear_all_tables())

    def _clear_all_tables(self):
        c = self._conn()
        try:
            for table in ["report_sources", "source_tags", "tags", "reports",
                           "summaries", "transcripts", "sources"]:
                c.execute(f"DELETE FROM {table}")
            c.commit()
        finally:
            c.close()

    def add_report_source(self, report_id: int, source_id: int):
        self._retry(lambda: self._add_report_source(report_id, source_id))

    def _add_report_source(self, report_id, source_id):
        c = self._conn()
        try:
            c.execute("INSERT OR IGNORE INTO report_sources (report_id, source_id) VALUES (?, ?)",
                       (report_id, source_id))
            c.commit()
        finally:
            c.close()