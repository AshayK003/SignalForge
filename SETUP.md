# SignalForge Setup

## Prerequisites

- Python 3.11+
- FFmpeg (for audio processing)
- Tesseract OCR (optional, for scanned PDFs)
- rclone (optional, for MEGA upload)

## Quick Start

```bash
# 1. Clone / enter the project
cd SignalForge

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your OpenRouter API key

# 4. Initialize database (auto-created on first run)
# The database is created at database/signalforge.db automatically

# 5. Run the app
streamlit run streamlit_app.py
```

## Configuration

All config is in `config.yaml` (defaults) and `.env` (secrets/overrides).

### LLM Provider

**Option A: OpenRouter (recommended)**
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_MODEL=google/gemini-2.0-flash-001
```

**Option B: Ollama (local, free)**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Cloud Upload (rclone)

```bash
# 1. Configure rclone with MEGA
rclone config

# 2. Set remote name in .env
RCLONE_REMOTE=mega
RCLONE_PATH=SignalForge
```

## Project Structure

```
SignalForge/
├── streamlit_app.py          # Entry point
├── pages/                    # Streamlit multipage UI
│   ├── 1_Dashboard.py
│   ├── 2_Ingest.py           # YouTube + file upload
│   ├── 3_Browse.py           # Browse sources/summaries
│   ├── 4_Reports.py          # Weekly reports
│   └── 5_Settings.py
├── app/
│   ├── ingestion/            # YouTube download, file handling
│   ├── extractors/           # PDF, OCR, text extraction
│   ├── transcription/        # faster-whisper wrapper
│   ├── summarization/        # Chunking, LLM pipeline, prompts
│   ├── reports/              # Weekly report generation, PDF/MD
│   ├── storage/              # SQLite CRUD + file manager
│   ├── cloud/                # rclone upload
│   └── utils/                # Config, logging, helpers
├── database/schema.py        # SQLite schema + init
├── prompts/                  # Prompt templates (Markdown)
├── templates/                # PDF report HTML templates
├── tests/                    # Unit + integration tests
├── config.yaml               # Default config
└── .env                      # Secrets (not checked in)
```

## Running Tests

```bash
pytest tests/ -v
```

## Data Flow

1. **Ingest** → YouTube URL or file upload
2. **Extract/Transcribe** → PDF text, audio transcription
3. **Chunk** → Split long text with overlap
4. **Summarize** → LLM chunk summaries → hierarchical synthesis
5. **Store** → SQLite (metadata) + files (transcripts, summaries)
6. **Report** → Weekly aggregation → PDF + Markdown
7. **Upload** → rclone to MEGA (optional)

## Troubleshooting

- **"No module named faster_whisper"** → `pip install faster-whisper` (requires C++ build tools)
- **"yt-dlp not found"** → `pip install yt-dlp`
- **OCR fails** → Install Tesseract: `choco install tesseract` (Windows) or `apt install tesseract-ocr`
- **PDF generation fails** → WeasyPrint may need additional system libs on Linux
