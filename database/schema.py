import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("SIGNALFORGE_DB", str(Path(__file__).parent / "signalforge.db"))

SCHEMA_SOURCES = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK(source_type IN ('youtube','pdf','text','audio','youtube_batch','manual')),
    title TEXT NOT NULL DEFAULT '',
    url TEXT,
    file_path TEXT,
    file_size INTEGER,
    metadata TEXT DEFAULT '{}',
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','completed','failed')),
    error TEXT
);
"""

SCHEMA_TAGS = """
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""

SCHEMA_SOURCE_TAGS = """
CREATE TABLE IF NOT EXISTS source_tags (
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, tag_id)
);
"""

SCHEMA_TRANSCRIPTS = """
CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    language TEXT DEFAULT 'unknown',
    duration_seconds REAL,
    segments TEXT DEFAULT '[]',
    model_used TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_SUMMARIES = """
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    level TEXT NOT NULL DEFAULT 'chunk' CHECK(level IN ('chunk','source','weekly')),
    parent_summary_id INTEGER REFERENCES summaries(id) ON DELETE SET NULL,
    summary_text TEXT NOT NULL,
    core_ideas TEXT DEFAULT '[]',
    insights TEXT DEFAULT '[]',
    action_items TEXT DEFAULT '[]',
    key_quotes TEXT DEFAULT '[]',
    themes TEXT DEFAULT '[]',
    technical_concepts TEXT DEFAULT '[]',
    opportunities TEXT DEFAULT '[]',
    contradictions TEXT DEFAULT '[]',
    why_it_matters TEXT DEFAULT '',
    open_questions TEXT DEFAULT '[]',
    model_used TEXT,
    chunk_index INTEGER,
    token_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    executive_summary TEXT,
    source_count INTEGER DEFAULT 0,
    local_pdf_path TEXT,
    local_md_path TEXT,
    cloud_pdf_url TEXT,
    cloud_md_url TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_REPORT_SOURCES = """
CREATE TABLE IF NOT EXISTS report_sources (
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    PRIMARY KEY (report_id, source_id)
);
"""

ALL_SCHEMAS = [
    SCHEMA_SOURCES,
    SCHEMA_TAGS,
    SCHEMA_SOURCE_TAGS,
    SCHEMA_TRANSCRIPTS,
    SCHEMA_SUMMARIES,
    SCHEMA_REPORTS,
    SCHEMA_REPORT_SOURCES,
]

SCHEMA_MIGRATIONS = [
    "ALTER TABLE summaries ADD COLUMN core_ideas TEXT DEFAULT '[]';",
    "ALTER TABLE summaries ADD COLUMN why_it_matters TEXT DEFAULT '';",
    "ALTER TABLE summaries ADD COLUMN open_questions TEXT DEFAULT '[]';",
]


def _migrate_source_type_constraint(conn: sqlite3.Connection):
    """Recreate sources table to add 'youtube_batch' and 'manual' to the CHECK constraint."""
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='sources';")
    row = cursor.fetchone()
    if not row:
        return
    sql = row["sql"]
    if "youtube_batch" in sql:
        return  # already migrated
    conn.executescript("""
        PRAGMA foreign_keys=OFF;
        CREATE TABLE sources_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('youtube','pdf','text','audio','youtube_batch','manual')),
            title TEXT NOT NULL DEFAULT '',
            url TEXT,
            file_path TEXT,
            file_size INTEGER,
            metadata TEXT DEFAULT '{}',
            ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','completed','failed')),
            error TEXT
        );
        INSERT INTO sources_new SELECT * FROM sources;
        DROP TABLE sources;
        ALTER TABLE sources_new RENAME TO sources;
        PRAGMA foreign_keys=ON;
    """)
    conn.commit()

SCHEMA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);",
    "CREATE INDEX IF NOT EXISTS idx_sources_ingested ON sources(ingested_at);",
    "CREATE INDEX IF NOT EXISTS idx_transcripts_source ON transcripts(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_summaries_source ON summaries(source_id);",
    "CREATE INDEX IF NOT EXISTS idx_summaries_level ON summaries(level);",
    "CREATE INDEX IF NOT EXISTS idx_reports_week ON reports(week_start);",
]


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    conn = get_connection(db_path)
    for schema in ALL_SCHEMAS:
        conn.execute(schema)
    for idx in SCHEMA_INDEXES:
        conn.execute(idx)
    for migration in SCHEMA_MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass
    _migrate_source_type_constraint(conn)
    conn.commit()
    return conn
