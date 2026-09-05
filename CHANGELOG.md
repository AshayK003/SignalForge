# Changelog

## [0.2.2] - 2026-09-05

### Fixed

- **Fail-closed access control** — empty `ALLOWED_USERS` no longer opens the
  bot to everyone; startup refuses without `ALLOWED_USERS` or
  `ALLOW_OPEN_BOT=1`. Both documented in `.env.example` and README.
- **YouTube URL allowlist** — `/ingest_youtube` and autodetect accept only
  real watch/shorts/live/embed URLs (`is_youtube_url` /
  `find_youtube_url`); downloads capped at 2 h (livestreams rejected).
- **Upload cap** — Telegram files over 20 MB are refused before download
  (`SIGNALFORGE_MAX_UPLOAD_BYTES`).
- **No more lost failures** — sources are recorded before summarization and
  marked `failed` on error (was: stuck `processing`, or no record at all).
- **Weekly report window** — one-sided bounds no longer reset the other;
  date-only end extended to end-of-day (Sundays were silently dropped);
  `/report` shows the just-created report via `report_id`.
- **Data correctness** — word-boundary chunk overlap with separator
  budgeting; `why_it_matters` lists normalized on insert; `generate_pdf`
  returns real `bytes`; `strip_markdown(None)` safe; upstream LLM bodies
  logged server-side, never raised to chat.
- **Hygiene** — untracked `.hermes/gfi_audit.json`, `.hermes/` ignored.

### Tests

- 28 new regression tests (`tests/test_audit_fixes.py`); full suite
  121 passed, `ruff check app/ tests/ database/` clean.

## [0.2.1] - 2026-08-24

### Added
- **Tests for YouTube ingestion** (`tests/test_youtube_ingestion.py`, 18
  tests): video-ID extraction across URL shapes, yt-dlp command construction
  (base flags, cookie handling), metadata parsing, download success/failure
  paths, and transcript fetching with API-error fallback. All external
  boundaries (subprocess + library) mocked; no network access. Closes #4.

## [0.2.0] - 2026-08-24

### Changed
- **Unified LLM layer:** the bot's private Gemini client is gone. `LLMClient`
  now speaks Gemini natively as a first-class provider alongside OpenRouter,
  DeepSeek, and Ollama, with a key-based fallback chain
  (primary -> any other keyed provider -> local Ollama).
- **`/report` no longer monkeypatches** `LLMClient.chat` at runtime; it uses
  the same shared client instance as every other command.
- Startup banner and report metadata reflect the actual configured provider
  and model instead of hardcoding Gemini.

### Added
- `[project.dependencies]` in pyproject.toml (was empty while requirements.txt
  carried 11 runtime deps), making `pip install .` work from metadata alone.
- This CHANGELOG.

### Fixed
- Rate-limit logging in the LLM path goes through the logger instead of
  `print()`.
