# SignalForge — AI Agent Context

This file is for AI coding agents (Claude Code, Cursor, etc.) to understand the project quickly.

## Project Overview

Local-first AI knowledge digest system. Personal use, single-user. Ingests content from YouTube, PDFs, audio files, and text — transcribes, summarizes, generates weekly intelligence reports.

## Architecture Principles

- **Minimal dependencies.** No LangChain, CrewAI, vector DBs, message queues, containers.
- **Single process.** Streamlit runs the pipeline inline. No workers or background jobs.
- **Functional pipeline.** Each stage is a function: `Input → Process → Store`.
- **Simple is correct.** If there are two ways to do something, pick the one with fewer files.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| UI | Streamlit (multipage) | Zero config, fast to build, good enough for 1 user |
| Language | Python 3.11+ | Obvious choice |
| Database | SQLite (WAL mode) | Zero config, one file, portable |
| STT | faster-whisper | Fast, accurate, local |
| PDF | pypdf | BSD license, no native deps |
| LLM | OpenRouter or Ollama | Config toggle, both OpenAI-compatible |
| PDF gen | WeasyPrint | HTML→PDF, full CSS control |
| Cloud | rclone | Supports 40+ providers, battle-tested |

## Project Structure

```
SignalForge/
├── streamlit_app.py          # Entry — redirects to dashboard
├── pages/                    # Streamlit multipage pages
│   ├── 1_Dashboard.py        # Stats overview
│   ├── 2_Ingest.py           # YouTube URL + file upload pipeline
│   ├── 3_Browse.py           # Browse sources, transcripts, summaries
│   ├── 4_Reports.py          # Weekly report generation + download
│   └── 5_Settings.py         # LLM, transcription, chunking config
├── app/
│   ├── ingestion/youtube.py  # yt-dlp wrapper: download audio + metadata
│   ├── ingestion/files.py    # File save + type classification
│   ├── extractors/pdf_extractor.py  # pypdf text extraction + OCR fallback
│   ├── extractors/text_extractor.py  # Plain text file reader
│   ├── transcription/transcriber.py  # faster-whisper wrapper
│   ├── summarization/chunker.py      # Text splitting with overlap
│   ├── summarization/llm_client.py   # OpenAI-compatible LLM client
│   ├── summarization/pipeline.py     # Chunk → summarize → synthesize → parse
│   ├── summarization/prompts.py      # Prompt template loader
│   ├── reports/generator.py          # Weekly aggregation + orchestration
│   ├── reports/pdf_gen.py            # WeasyPrint PDF from HTML template
│   ├── reports/md_gen.py             # Markdown report generation
│   ├── storage/db.py                 # SQLite CRUD (sources, transcripts, summaries, reports, tags)
│   ├── storage/files.py              # Local file path manager
│   ├── cloud/rclone_uploader.py      # rclone subprocess wrapper
│   └── utils/config.py              # YAML + env config loader
│   └── utils/helpers.py             # hashing, slugify, date helpers
│   └── utils/logging.py             # Logging setup
├── database/schema.py       # SQLite schema + init (7 tables, indexes)
├── prompts/                 # LLM prompt templates (Markdown)
│   ├── summarize_chunk.md
│   ├── synthesize.md
│   ├── extract_insights.md
│   └── weekly_report.md
├── templates/report.html    # PDF HTML template + CSS
├── tests/                   # Pytest tests (24 passing)
├── config.yaml              # Default configuration
├── .env.example             # Secrets template
├── requirements.txt         # Python dependencies
└── streamlit_app.py         # Main entry point
```

## Data Flow

```
User Input (YouTube URL / file upload)
  → Ingest (download audio / save file)
  → Extract/Transcribe (pypdf / faster-whisper)
  → Chunk (overlapping segments)
  → LLM Summarize (per chunk, then synthesize)
  → Store (SQLite + file system)
  → Weekly aggregator (collects all source summaries)
  → Report generator (LLM synthesis → PDF + Markdown)
  → Cloud upload (optional rclone)
```

## SQLite Schema (7 tables)

`sources`, `transcripts`, `summaries`, `reports`, `tags`, `source_tags`, `report_sources`

All with timestamps, foreign keys, cascading deletes. WAL mode for performance.

## Key Conventions

- **No ORM.** Raw SQL via `sqlite3.Row` — explicit, debuggable, no magic.
- **No serializers.** JSON fields stored as text, parsed in application code.
- **No config in code.** Config lives in `config.yaml` + `.env`, loaded via `app.utils.config`.
- **LLM outputs JSON.** Pipeline expects structured JSON from LLM, with plain-text fallback.
- **Tests live in `tests/`.** Run with `pytest tests/ -v`.
- **Prompts are files.** Edit `prompts/*.md` to change LLM behavior without touching code.

## Common Tasks

**Add a new source type:**
1. Classify it in `app/ingestion/files.py`
2. Add an extractor in `app/extractors/`
3. Handle it in `pages/2_Ingest.py`

**Change summarization behavior:**
Edit `prompts/summarize_chunk.md` (or the other prompt files).

**Add a new database field:**
1. Update `database/schema.py` (ALTER TABLE or add column)
2. Update `app/storage/db.py` (insert/query methods)
3. Update relevant prompt templates if the field is LLM-generated

**Switch LLM provider:**
Set `LLM_PROVIDER=ollama` in `.env`. The client auto-switches base URL and model.

## Non-Goals

- Multi-user support (personal tool)
- Vector search (SQLite FTS5 is sufficient)
- Real-time processing (synchronous pipeline, fine for <100 sources/week)
- Mobile app (Streamlit web UI only)
- Enterprise deployment (no containers, no orchestrators)
