# SignalForge — AI Agent Context

This file is for AI coding agents (Claude Code, Cursor, etc.) to understand the project quickly.

## Project Overview

Local-first AI knowledge digest system. Personal use, single-user. Ingests content from YouTube, PDFs, audio files, and text — transcribes, summarizes using the PACE-X analysis framework, generates weekly intelligence reports. Interface is a Telegram bot powered by Gemini LLM, with Hermes Agent gateway as the primary entry point.

## Architecture Principles

- **Minimal dependencies.** No LangChain, CrewAI, vector DBs, message queues, containers.
- **Single process.** Telegram bot runs the pipeline inline. No workers or background jobs.
- **Functional pipeline.** Each stage is a function: `Input → Process → Store`.
- **Simple is correct.** If there are two ways to do something, pick the one with fewer files.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Interface | Telegram Bot (python-telegram-bot) | Mobile-first, zero UI code |
| Gateway | Hermes Agent (optional) | Full AI agent with tools, memory, skills |
| Language | Python 3.12 | Obvious choice |
| Database | SQLite (WAL mode) | Zero config, one file, portable |
| STT | youtube-transcript-api / faster-whisper | YouTube captions (instant) + audio fallback |
| PDF text | pypdf | BSD license, no native deps |
| LLM | Gemini 2.5 Flash (Google AI Studio) | Free tier, 1500 req/day |
| PDF gen | fpdf2 + Segoe UI font | Zero native DLLs, Unicode support |
| Cloud | rclone | Supports 40+ providers, battle-tested |

## Project Structure

```
SignalForge/
├── bot.py                     # Telegram bot — all handlers + Gemini LLM
├── hermes_agent.py            # Hermes agent entry point (fallback to bot.py)
├── start_hermes.bat           # Double-click to start Hermes gateway
├── start_hermes.ps1           # PowerShell launcher with cleanup
├── run_bot.bat                # Direct bot.py launcher
├── run_bot.ps1                # PowerShell bot launcher with logging
├── app/
│   ├── ingestion/youtube.py   # yt-dlp wrapper: captions + audio download
│   ├── extractors/pdf_extractor.py   # pypdf text extraction + OCR fallback
│   ├── extractors/text_extractor.py  # Plain text file reader
│   ├── transcription/transcriber.py  # faster-whisper wrapper
│   ├── summarization/chunker.py      # Text splitting with overlap
│   ├── summarization/llm_client.py   # OpenAI-compatible LLM client
│   ├── summarization/prompts.py      # Prompt template loader
│   ├── reports/generator.py          # Weekly aggregation + orchestration
│   ├── reports/pdf_gen.py            # fpdf2 PDF with Segoe UI font
│   ├── reports/md_gen.py             # Markdown report generation
│   ├── storage/db.py                 # SQLite CRUD (sources, transcripts, summaries, reports, tags)
│   ├── storage/files.py              # Local file path manager
│   └── utils/
│       ├── config.py                 # YAML + env config loader
│       ├── deps.py                   # External tool path management
│       └── helpers.py                # Date helpers, safe filenames, JSON parsing
├── database/schema.py         # SQLite schema + init (7 tables, indexes)
├── prompts/                   # LLM prompt templates (Markdown)
│   ├── pace_x_system.md       # PACE-X system prompt
│   ├── summarize_chunk.md     # Per-chunk summarization
│   ├── synthesize.md          # Multi-chunk synthesis
│   └── weekly_report.md       # Weekly report generation
├── tests/                     # Pytest tests (27 passing)
├── .env                       # Secrets (API keys, bot token) — gitignored
├── .env.example               # Secrets template
├── config.yaml                # Default configuration
├── requirements.txt           # Python dependencies
├── AGENTS.md                  # This file
└── HERMES_AGENT_SPEC.md       # Hermes agent specification
```

## Data Flow

```
User sends message via Telegram
  → Bot receives (YouTube URL / file / text)
  → Ingest (download audio / save file)
  → Extract/Transcribe (pypdf / faster-whisper / YouTube captions)
  → Chunk (overlapping segments, 3000 chars + 300 overlap)
  → LLM Summarize with PACE-X (per chunk, then synthesize)
  → Store (SQLite + file system)
  → Reply with summary to user
  → Weekly aggregator (collects all source summaries)
  → Report generator (LLM synthesis → PDF + Markdown)
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
- **Auth via env var.** Set `ALLOWED_USERS` in `.env` with comma-separated Telegram user IDs.

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with available commands |
| `/ingest_youtube <url>` | Ingest a YouTube video |
| `/ingest_text <text>` | Paste text/transcript for analysis |
| `/summary <id>` | Get PACE-X summary for a source |
| `/list` | List recent sources with status |
| `/report` | Generate weekly intelligence report |
| `/search <query>` | Search sources by title |
| `/status` | Show system stats |
| File upload | Send PDF, audio, or text file directly |

## PACE-X Analysis Fields

Every summary includes these structured fields:
- **summary** — concise overview
- **core_ideas** — key concepts/arguments
- **insights** — original analysis/connections
- **action_items** — concrete takeaways
- **key_quotes** — notable excerpts
- **themes** — cross-cutting topics
- **technical_concepts** — specialized terminology
- **opportunities** — actionable angles
- **contradictions** — surprising/contrarian points
- **why_it_matters** — significance/impact
- **open_questions** — unresolved areas

## Common Tasks

**Add a new source type:**
1. Add extraction logic in `app/extractors/`
2. Handle the new file type in `bot.py` `handle_file()` function
3. Update file type detection in `handle_file()`

**Change summarization behavior:**
Edit `prompts/summarize_chunk.md` (or the other prompt files).

**Add a new database field:**
1. Update `database/schema.py` (ALTER TABLE or add column)
2. Update `app/storage/db.py` (insert/query methods)
3. Update relevant prompt templates if the field is LLM-generated

**Switch LLM model:**
Set `GEMINI_MODEL=gemini-2.5-flash` in `.env`. The bot uses Gemini directly via REST API.

**Add a new bot command:**
1. Create handler function in `bot.py`
2. Register with `app.add_handler(CommandHandler("command_name", handler))`
3. Update the `/start` message to list the new command

## Security Notes

- API keys are passed via HTTP headers (not URL query strings)
- User authentication via `ALLOWED_USERS` env var (comma-separated Telegram user IDs)
- Error messages shown to users are generic; full details logged server-side
- `.env` is gitignored — never commit secrets

## Non-Goals

- Multi-user support (personal tool)
- Vector search (SQLite FTS5 is sufficient)
- Real-time processing (synchronous pipeline, fine for <100 sources/week)
- Mobile app (Telegram bot IS the mobile interface)
- Enterprise deployment (no containers, no orchestrators)
