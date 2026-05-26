# SignalForge 📡

**Local-first AI knowledge digest system.** Transform YouTube videos, PDFs, audio files, and text into structured weekly intelligence reports — all running locally with open-source tooling.

## Features

- **Ingest anything** — YouTube links, PDFs, audio files, text files
- **Transcribe** — Speech-to-text via faster-whisper (multilingual, timestamped)
- **Extract** — PDF text extraction with OCR fallback for scanned docs
- **Summarize** — Hierarchical LLM summarization (chunk → synthesize → structured insights)
- **Weekly reports** — Auto-generated PDF + Markdown with executive summary, themes, action items, contradictions, opportunities
- **Cloud backup** — Optional rclone upload to MEGA or any cloud storage
- **Local-first** — Everything stored in SQLite + local files. No data leaves your machine except LLM API calls.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure (copy and edit)
cp .env.example .env

# Run
streamlit run streamlit_app.py
```

Requires Python 3.11+, FFmpeg, and optionally Tesseract OCR and rclone.

## Architecture

```
streamlit_app.py → 5 UI pages (Streamlit multipage)
  ├─ ingestion/     → YouTube (yt-dlp), file upload
  ├─ extractors/    → PDF (pypdf), OCR (Tesseract)
  ├─ transcription/ → faster-whisper
  ├─ summarization/ → chunker → LLM pipeline → structured output
  ├─ reports/       → weekly aggregation → WeasyPrint PDF + Markdown
  ├─ storage/       → SQLite (7 tables) + local file manager
  ├─ cloud/         → rclone upload wrapper
  └─ utils/         → config, logging, helpers
```

**Tech stack:** Python, Streamlit, SQLite, faster-whisper, yt-dlp, pypdf, WeasyPrint, OpenRouter/Ollama.

## License

MIT
