# SignalForge 📡

**Local-first AI knowledge digest system.** Transform YouTube videos, PDFs, audio files, and text into structured weekly intelligence reports — all running locally with open-source tooling.

## Features

- **Ingest anything** — YouTube links (batch support), PDFs, audio files, text files
- **Transcribe** — Instant YouTube captions via `youtube-transcript-api`, audio fallback via `faster-whisper`
- **Extract** — PDF text via `pypdf` with Tesseract OCR fallback for scanned/image-based PDFs
- **Summarize** — PACE-X structured analysis (summary, core ideas, insights, action items, key quotes, themes, contradictions, opportunities, why it matters, open questions)
- **Parallel processing** — Batch YouTube summarization via `ThreadPoolExecutor`, combined synthesis across videos
- **Weekly reports** — Auto-generated PDF (`fpdf2`) + Markdown with executive summary, themes, insights, action items, contradictions
- **LLM agnostic** — Toggle between OpenRouter (cloud) and Ollama (local) at runtime
- **Cloud backup** — Optional rclone upload to MEGA or any of 40+ providers
- **Local-first** — Everything stored in SQLite + local files. No data leaves your machine except LLM API calls.

## Quick Start

```powershell
# Install Python dependencies
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env to set OPENROUTER_API_KEY or switch to LLM_PROVIDER=ollama

# Run (recommended — sets up PATH for ffmpeg, deno, poppler, tesseract)
.\start_app.ps1
```

Or without the launcher script:
```bash
streamlit run streamlit_app.py
```

### Prerequisites (Windows)

These are auto-detected if installed via winget. The `start_app.ps1` launcher injects them into PATH:

| Dependency | Install Command | Purpose |
|-----------|----------------|---------|
| FFmpeg | `winget install yt-dlp.FFmpeg` | Audio conversion for yt-dlp |
| Deno | `winget install DenoLand.Deno` | JS runtime for yt-dlp YouTube extraction |
| Poppler | `winget install oschwartz10612.Poppler` | PDF→image for OCR |
| Tesseract OCR | `winget install UB-Mannheim.TesseractOCR` | OCR for image-based PDFs |

## Architecture

```
streamlit_app.py → 5 UI pages (Streamlit multipage)
  ├─ pages/
  │   ├─ 1_Dashboard.py    Stats, recent activity, quick actions
  │   ├─ 2_Ingest.py       YouTube batch + file upload pipeline
  │   ├─ 3_Browse.py       Search/filter sources, transcripts, summaries
  │   ├─ 4_Reports.py      Weekly report generation + PDF/MD download
  │   └─ 5_Settings.py     LLM, transcription, chunking, reset
  ├─ app/
  │   ├─ ingestion/        YouTube (yt-dlp), file save + classification
  │   ├─ extractors/       PDF (pypdf), OCR (Tesseract), text
  │   ├─ transcription/    faster-whisper wrapper
  │   ├─ summarization/    chunker → LLM pipeline → PACE-X structured output
  │   ├─ reports/          Weekly aggregation → fpdf2 PDF + Markdown
  │   ├─ storage/          SQLite (7 tables, WAL mode) + file manager
  │   ├─ cloud/            rclone upload wrapper
  │   ├─ ui/               Reusable components (render_summary)
  │   └─ utils/            Config (YAML + .env), logging, helpers
  ├─ database/schema.py    Schema + migrations (7 tables, indexes)
  ├─ prompts/              LLM prompt templates (Markdown)
  └─ tests/                24 pytest tests
```

### Data Flow

```
User Input (YouTube URLs / file upload)
  → Ingest (captions or download audio / save file)
  → Extract/Transcribe (pypdf / faster-whisper)
  → Chunk (overlapping segments)
  → LLM Summarize with PACE-X (per chunk, then synthesize)
  → Store (SQLite + file system)
  → Weekly aggregator (collects all source summaries)
  → Report generator (LLM synthesis → fpdf2 PDF + Markdown)
  → Cloud upload (optional rclone)
```

### PACE-X Analysis Fields

Every LLM summary produces these structured fields:
- **summary** — Concise overview of the content
- **core_ideas** — Key concepts and arguments
- **insights** — Original analysis and cross-domain connections
- **action_items** — Concrete, actionable takeaways
- **key_quotes** — Notable excerpts from the source
- **themes** — Cross-cutting topics and patterns
- **technical_concepts** — Specialized terminology
- **opportunities** — Actionable angles and applications
- **contradictions** — Surprising or contrarian points
- **why_it_matters** — Significance and broader impact
- **open_questions** — Unresolved areas and future directions

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| UI | Streamlit (multipage) | Zero config, fast to build, good enough for 1 user |
| Language | Python 3.12 | Obvious choice |
| Database | SQLite (WAL mode) | Zero config, one file, portable |
| STT | youtube-transcript-api / faster-whisper | YouTube captions (instant) + audio fallback |
| PDF text | pypdf | BSD license, no native deps |
| PDF OCR | pdf2image + Tesseract 5.4 | Scanned/image-based PDF support |
| LLM | OpenRouter or Ollama | Config toggle, both OpenAI-compatible |
| PDF gen | fpdf2 + Segoe UI font | Zero native DLLs, Unicode support |
| Cloud | rclone | Supports 40+ providers, battle-tested |

## License

MIT
