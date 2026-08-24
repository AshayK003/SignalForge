# Changelog

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
