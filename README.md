# SignalForge

Local-first AI knowledge digest system. Transform YouTube videos, PDFs, audio files, and text into structured intelligence — all running locally with open-source tooling.

## What It Does

- **Ingest** — YouTube links, PDFs, audio files, text pastes
- **Transcribe** — Instant YouTube captions, audio fallback via faster-whisper
- **Analyze** — PACE-X structured analysis (summary, insights, action items, contradictions, etc.)
- **Report** — Weekly intelligence reports as PDF + Markdown
- **Chat** — Ask questions about your ingested content via Telegram

## Quick Start

### Option 1: Hermes Agent Gateway (Recommended)

```powershell
# Double-click or run:
.\start_hermes.bat
```

This starts the Hermes Agent gateway, which connects to Telegram and provides the full AI agent experience with tools, memory, and skills.

### Option 2: Direct Bot

```powershell
# Install dependencies
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env to set GEMINI_API_KEY and TELEGRAM_BOT_TOKEN

# Run
.\run_bot.bat
```

### Prerequisites

| Dependency | Purpose | Required |
|-----------|---------|----------|
| Python 3.12+ | Runtime | Yes |
| FFmpeg | Audio conversion for yt-dlp | For YouTube audio |
| Tesseract OCR | OCR for scanned PDFs | For PDF extraction |
| Hermes Agent | AI gateway with Telegram integration | Optional |

### Configuration

Copy `.env.example` to `.env` and fill in:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
GEMINI_API_KEY=your_gemini_key

# Optional — restrict bot access
ALLOWED_USERS=your_telegram_user_id

# Optional — switch models
GEMINI_MODEL=gemini-2.5-flash
```

Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot).

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/ingest_youtube <url>` | Ingest a YouTube video |
| `/ingest_text <text>` | Paste text for analysis |
| `/summary <id>` | View PACE-X summary |
| `/list` | List recent sources |
| `/report` | Generate weekly report |
| `/search <query>` | Search sources |
| `/status` | System stats |
| File upload | Send PDF, audio, or text |

## Architecture

```
Telegram User
  → Bot (bot.py)
    → Ingest (YouTube/PDF/audio/text)
    → Extract & Transcribe
    → Chunk (3000 chars + 300 overlap)
    → Gemini LLM (PACE-X analysis)
    → Store (SQLite + files)
    → Reply with summary
```

### Tech Stack

| Layer | Choice |
|-------|--------|
| Interface | Telegram Bot (python-telegram-bot) |
| Gateway | Hermes Agent (optional) |
| Language | Python 3.12 |
| Database | SQLite (WAL mode) |
| LLM | Gemini 2.5 Flash (Google AI Studio) |
| STT | youtube-transcript-api / faster-whisper |
| PDF | pypdf + fpdf2 |

### PACE-X Analysis Fields

Every summary includes:
- **summary** — Executive overview
- **core_ideas** — Key concepts
- **insights** — Original analysis
- **action_items** — Concrete takeaways
- **key_quotes** — Notable excerpts
- **themes** — Cross-cutting topics
- **technical_concepts** — Specialized terminology
- **opportunities** — Actionable angles
- **contradictions** — Contrarian points
- **why_it_matters** — Strategic significance
- **open_questions** — Unresolved areas

## Project Structure

```
SignalForge/
├── bot.py                 # Telegram bot + Gemini LLM
├── start_hermes.bat       # Hermes gateway launcher
├── start_hermes.ps1       # PowerShell launcher
├── run_bot.bat            # Direct bot launcher
├── run_bot.ps1            # PowerShell bot launcher
├── app/
│   ├── ingestion/         # YouTube (yt-dlp)
│   ├── extractors/        # PDF, text extraction
│   ├── transcription/     # faster-whisper
│   ├── summarization/     # Chunker, LLM client, prompts
│   ├── reports/           # PDF + Markdown generation
│   ├── storage/           # SQLite + file manager
│   └── utils/             # Config, deps, helpers
├── database/schema.py     # SQLite schema (7 tables)
├── prompts/               # LLM prompt templates
├── tests/                 # 27 pytest tests
├── config.yaml            # Default configuration
└── .env                   # Secrets (gitignored)
```

## Development

```bash
# Run tests
pytest tests/ -v

# Lint check
python -m py_compile bot.py
python -m py_compile app/storage/db.py
```

## License

MIT

---

## Developer Support

If SignalForge helps your workflow, consider supporting the developer:

<a href="https://chai4.me/darkcharon3301" target="_blank" title="Support darkcharon3301 on Chai4Me" style="display:inline-flex;flex-direction:column;align-items:center;justify-content:center;background:#ffffff;padding:8px 32px;border-radius:16px;text-decoration:none;border:1px solid #e5e7eb;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);transition:transform 0.2s;"><img src="https://chai4.me/icons/wordmark.png" alt="Chai4Me" style="height:32px;object-fit:contain;margin-bottom:4px;"/><span style="color:#6b7280;font-family:sans-serif;font-size:14px;font-weight:600;">@darkcharon3301</span></a>
