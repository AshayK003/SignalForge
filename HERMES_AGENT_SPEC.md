# SignalForge — Hermes Agent Specification

## Project Intent

A local-first AI knowledge digest system for a single user. Ingests content from YouTube, PDFs, audio files, and plain text — transcribes, summarizes using the PACE-X analysis framework, generates weekly intelligence reports, and optionally uploads to cloud storage.

The user abandoned the Streamlit UI + Ollama local approach due to infrastructure friction (GPU setup, rate limits on cloud APIs, database locking issues, etc.). The goal now is to replicate all functionality through a **Hermes agent** connected to a **Telegram bot**, powered by a **free unlimited cloud AI model**.

## User Environment

- **OS:** Windows 11
- **GPU:** NVIDIA GeForce RTX 3050 Laptop 6GB
- **Python:** 3.12
- **Existing project:** `D:\Personal projects\SignalForge\` (can reuse modules)

## Core Requirements

### 1. Input Sources
- **YouTube URLs** — extract transcripts (via youtube-transcript-api for captions, yt-dlp + faster-whisper for audio fallback)
- **PDF files** — extract text via pypdf
- **Audio files** — transcribe via faster-whisper
- **Manual text** — user pastes transcript/text directly

### 2. Content Processing (PACE-X Framework)
Every piece of content must be analyzed through PACE-X (Precise Analysis, Compilation, Extraction, and Synthesis), producing structured JSON output with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | High-density executive summary (2-3 paragraphs) |
| `core_ideas` | string[] | Key concepts explained clearly |
| `insights` | string[] | Strongest insights and implications |
| `action_items` | string[] | Practical takeaways and implementation ideas |
| `key_quotes` | string[] | Important verbatim quotes |
| `themes` | string[] | Recurring themes and topics |
| `technical_concepts` | string[] | Specialized terminology |
| `opportunities` | string[] | Actionable implied opportunities |
| `contradictions` | string[] | Contrarian points and tensions |
| `why_it_matters` | string | Broader significance and strategic impact |
| `open_questions` | string[] | Unresolved issues |

For long content (>3000 chars), chunk the text with 300-char overlap, summarize each chunk, then synthesize into one unified analysis.

### 3. Weekly Intelligence Reports
- Aggregate all source summaries from the current week
- Generate a synthesized report with these sections:
  - `executive_summary` — high-density narrative
  - `key_developments` — ordered by importance
  - `cross_source_connections` — connections/contradictions between sources
  - `recommended_actions` — concrete decisions to follow
  - `signals_to_monitor` — trends worth watching

### 4. Telegram Bot Interface
The bot should support these commands:

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with available commands |
| `/ingest_youtube <url>` | Ingest a YouTube video (captions first, audio fallback) |
| `/ingest_text <text>` | Ingest manually pasted text/transcript |
| `/summary <id>` | Get the PACE-X summary for a source |
| `/list` | List recent sources with status |
| `/report` | Generate or retrieve this week's intelligence report |
| `/search <query>` | Search across source titles |
| `/status` | Show system stats (sources processed, reports generated) |

### 5. Data Storage
- **SQLite** (single file, zero config) with WAL mode
- Tables: `sources`, `transcripts`, `summaries`, `reports`, `tags`, `source_tags`, `report_sources`
- All with timestamps, foreign keys, cascading deletes
- Source type constraint: `youtube`, `pdf`, `text`, `audio`, `youtube_batch`, `manual`
- Summary JSON fields stored as text, parsed in application code

### 6. Optional Features
- **Rclone cloud upload** — backup reports to Mega (or any of 40+ providers)
- **Search** — SQLite FTS5 or basic LIKE search on titles and summaries

## Architecture Considerations

### Processing Flow
```
User sends YouTube URL / file / text via Telegram
  → Bot receives message
  → Transcribe/extract (if needed)
  → Chunk text (3000 chars + 300 overlap)
  → LLM analyze each chunk (PACE-X)
  → Synthesize chunk summaries into unified analysis
  → Store in SQLite
  → Reply with summary to user
```

### Chunking Strategy
- `max_chunk_size`: 3000 characters
- `overlap`: 300 characters (prevents context loss at boundaries)
- Each chunk gets the previous chunk's tail as `overlap_prefix`
- For multi-chunk content: summarize each in parallel, then run one synthesis pass

### Prompt Templates
The agent should use these system prompts (already defined in `prompts/`):

**PACE-X System Prompt** (`prompts/pace_x_system.md`):
The LLM persona is PACE-X — an elite research analyst that produces structured intelligence, not shallow summaries. Returns JSON with the 11 fields listed above.

**Chunk Summarization** (`prompts/summarize_chunk.md`):
```
Apply PACE-X analysis to this section of "{title}".

Content:
{text}
```

**Synthesis** (`prompts/synthesize.md`):
```
Apply PACE-X analysis to synthesize these chunk summaries of "{title}" into a unified analysis.

Chunk Summaries:
{summaries}
```

**Weekly Report** (`prompts/weekly_report.md`):
```
You are generating a weekly intelligence report for {week_start} to {week_end}.
{source_count} sources were processed this week. Here are their summaries:
{sources}
Produce a structured report as JSON...
```

## Free Unlimited Cloud AI Model Options

| Provider | Model | Free Tier | Truly Unlimited? |
|----------|-------|-----------|-----------------|
| **DeepSeek API** | `deepseek-chat` (v4 flash) | ~$5-10 free credit on signup | No — credits run out |
| **OpenRouter** | `deepseek/deepseek-v4-flash:free` | 50 requests/day | No — daily limit |
| **Google Gemini** | `gemini-2.0-flash` | 1500 requests/day | No — daily limit |
| **Groq** | `llama-3.3-70b` | 30 req/min, 14400/day | No — rate limited |
| **GitHub Models** | `gpt-4o-mini` | Limited free requests/month | No — monthly cap |
| **Local Ollama** | `qwen3:8b` (already pulled) | Unlimited | **Yes** — but requires local GPU |

**Recommendation:** DeepSeek direct API (`deepseek-chat`, via `api.deepseek.com/v1`) gives the most generous free credits and supports JSON mode. When credits run out, fall back to Ollama local (Qwen3:8b fits your RTX 3050 6GB).

## Non-Goals (Intentionally Excluded)
- Multi-user support (personal tool only)
- Vector search / embeddings (SQLite is sufficient)
- Real-time processing (fine for <100 sources/week)
- Mobile app (Telegram bot IS the mobile interface)
- Containerization (single Python process)
- Complex orchestration frameworks (no LangChain, CrewAI, etc.)

## Expected User Behavior
- User sends YouTube URLs via Telegram chat
- User uploads PDF/audio files via Telegram
- User pastes text directly for quick summarization
- User requests weekly report every few days
- All interactions happen async — bot processes and replies when done
- Single user, no authentication needed beyond Telegram bot token
