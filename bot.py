import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid %s — using default %d", name, default)
        return default


ALLOWED_USERS = set(filter(None, os.getenv("ALLOWED_USERS", "").split(",")))

# Upload/download abuse caps (bytes / seconds, overridable via env).
MAX_UPLOAD_BYTES = _env_int("SIGNALFORGE_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)

from app.storage.db import Database
from app.storage.files import FileManager
from app.summarization.chunker import chunk_text
from app.summarization.llm_client import LLMClient
from app.summarization.prompts import PromptLibrary
from app.utils.config import load_config
from app.utils.helpers import parse_json_field, week_boundary

cfg = load_config()
db = Database()
files = FileManager(cfg.app.data_dir)
prompts = PromptLibrary()
DATA_DIR = Path(cfg.app.data_dir)

# Shared LLM client - single instance, provider chain from config (openrouter/deepseek/gemini/ollama)
llm = LLMClient(cfg, logger=logger)


def _llm_chat(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """Call the shared LLMClient; json_mode maps to response_format."""
    response_format = {"type": "json_object"} if json_mode else None
    return llm.chat(messages, temperature=temperature, max_tokens=max_tokens, response_format=response_format)


def _llm_model() -> str:
    return {
        "openrouter": cfg.llm.openrouter_model,
        "deepseek": cfg.llm.deepseek_model,
        "ollama": cfg.llm.ollama_model,
    }.get(cfg.llm.provider, cfg.llm.gemini_model)


def parse_llm_json(response: str) -> dict:
    json_match = __import__("re").search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if json_match:
        response = json_match.group(1).strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"summary": response[:5000]}


def pacex_summarize(text: str, title: str = "") -> dict:
    system = prompts.load("pace_x_system")
    chunks = chunk_text(text, cfg.chunking.max_chunk_size, cfg.chunking.overlap)
    chunk_summaries = []
    for _i, chunk in enumerate(chunks):
        chunk_text_content = chunk["text"]
        if chunk.get("overlap_prefix"):
            chunk_text_content = (
                f"[Previous chunk context]\n{chunk['overlap_prefix']}\n\n[Current chunk]\n{chunk_text_content}"
            )
        prompt = prompts.render("summarize_chunk", text=chunk_text_content, title=title)
        response = _llm_chat(
            [{"role": "user", "content": prompt}],
            system_prompt=system,
            json_mode=True,
        )
        chunk_summaries.append(parse_llm_json(response))

    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    summaries_text = "\n\n---\n\n".join(_format_chunk(i, s) for i, s in enumerate(chunk_summaries))
    prompt = prompts.render("synthesize", summaries=summaries_text, title=title)
    response = _llm_chat(
        [{"role": "user", "content": prompt}],
        system_prompt=system,
        json_mode=True,
    )
    result = parse_llm_json(response)
    defaults = {
        "summary": "",
        "core_ideas": [],
        "insights": [],
        "action_items": [],
        "key_quotes": [],
        "themes": [],
        "technical_concepts": [],
        "opportunities": [],
        "contradictions": [],
        "why_it_matters": "",
        "open_questions": [],
    }
    return {**defaults, **result}


def _format_chunk(i: int, s: dict) -> str:
    parts = [f"Chunk {i + 1}:", f"Summary: {s.get('summary', '')}"]
    themes = s.get("themes", [])
    if themes:
        parts.append(f"Themes: {', '.join(themes[:5])}")
    insights = s.get("insights", [])
    if insights:
        parts.append(f"Insights: {'; '.join(insights[:5])}")
    return "\n".join(parts)


# ── Telegram Bot ────────────────────────────────────────────────────────

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


def _is_authorized(update: Update) -> bool:
    # Fail closed: an empty allowlist only permits traffic when the operator
    # explicitly opts into an open bot (personal-use mode).
    if not ALLOWED_USERS:
        return os.getenv("ALLOW_OPEN_BOT", "") == "1"
    return str(update.effective_user.id) in ALLOWED_USERS


async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "📡 *SignalForge Bot*\n\n"
        "I ingest content from YouTube, text, and files — then analyze them with AI.\n\n"
        "*Commands:*\n"
        "`/ingest_youtube <url>` — Ingest a YouTube video\n"
        "`/ingest_text <text>` — Paste text/transcript\n"
        "`/summary <id>` — Get PACE-X summary\n"
        "`/list` — List recent sources\n"
        "`/report` — Generate weekly report\n"
        "`/search <query>` — Search sources\n"
        "`/status` — System stats",
        parse_mode="Markdown",
    )


async def ingest_youtube(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    url = " ".join(ctx.args)
    if not url:
        await update.message.reply_text("Usage: `/ingest_youtube <url>`", parse_mode="Markdown")
        return
    from app.ingestion.youtube import is_youtube_url
    if not is_youtube_url(url):
        await update.message.reply_text(
            "Usage: `/ingest_youtube <url>` — YouTube watch/shorts/live links only.",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("📥 Processing YouTube video...")
    source_id = None
    try:
        from app.ingestion.youtube import download_audio, extract_metadata, get_captions
        from app.transcription.transcriber import Transcriber

        caption_result = get_captions(url, str(DATA_DIR / "temp"))
        if caption_result:
            text = caption_result["text"]
            transcript_data = {
                "text": text,
                "language": "en",
                "duration_seconds": caption_result.get("duration_seconds"),
                "segments": [],
                "model_used": "youtube-captions",
            }
            meta = extract_metadata(url)
            title = meta.get("title", url)
            await msg.edit_text(f"✅ Captions fetched — {len(text):,} chars\n🧠 Summarizing...")
        else:
            await msg.edit_text("⬇️ No captions — downloading audio...")
            result = download_audio(url, str(DATA_DIR / "temp"))
            audio_path = result.get("audio_path", "")
            if not audio_path or not Path(audio_path).exists():
                raise RuntimeError("Audio download failed")
            t = Transcriber(cfg.transcription.model, cfg.transcription.device, cfg.transcription.compute_type)
            transcript_data = t.transcribe(audio_path)
            text = transcript_data["text"]
            title = result.get("title", url)
            await msg.edit_text(f"✅ Transcribed — {len(text):,} chars\n🧠 Summarizing...")

        source_id = db.insert_source(
            "youtube", title=title, url=url, metadata={"method": transcript_data.get("model_used", "unknown")}
        )
        db.update_source_status(source_id, "processing")
        summary = pacex_summarize(text, title)

        files.save_transcript(source_id, text, "txt")
        db.insert_transcript(
            source_id,
            text=text,
            language=transcript_data.get("language", "en"),
            duration_seconds=transcript_data.get("duration_seconds"),
            segments=transcript_data.get("segments", []),
            model_used=transcript_data.get("model_used", "youtube-captions"),
        )
        db.insert_summary(
            source_id,
            level="source",
            summary_text=summary.get("summary", ""),
            core_ideas=summary.get("core_ideas"),
            insights=summary.get("insights"),
            action_items=summary.get("action_items"),
            key_quotes=summary.get("key_quotes"),
            themes=summary.get("themes"),
            technical_concepts=summary.get("technical_concepts"),
            opportunities=summary.get("opportunities"),
            contradictions=summary.get("contradictions"),
            why_it_matters=summary.get("why_it_matters"),
            open_questions=summary.get("open_questions"),
            model_used=f"{cfg.llm.provider}/{_llm_model()}",
        )
        files.save_summary(source_id, json.dumps(summary, indent=2))
        db.update_source_status(source_id, "completed")

        reply = f"✅ *{title[:80]}*\n\n📝 *Summary:*\n{summary.get('summary', '(empty)')[:1000]}"
        await msg.edit_text(reply, parse_mode="Markdown")

    except Exception:
        logger.exception("ingest_youtube error")
        if source_id:
            try:
                db.update_source_status(source_id, "failed")
            except Exception:
                logger.warning("could not mark source %s failed", source_id)
        await msg.edit_text("❌ Something went wrong. Check logs for details.")


async def ingest_text_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Usage: `/ingest_text <text>`", parse_mode="Markdown")
        return
    try:
        text = validate_user_input(text)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid input ({categorize_error(e)}). Send non-empty text under 4000 chars."
        )
        return

    msg = await update.message.reply_text("🧠 Analyzing...")
    source_id = None
    try:
        title = f"Manual Entry {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        source_id = db.insert_source("manual", title=title)
        db.update_source_status(source_id, "processing")
        summary = pacex_summarize(text, title)
        files.save_transcript(source_id, text, "txt")
        db.insert_transcript(source_id, text=text, language="en", segments=[], model_used="manual")
        db.insert_summary(
            source_id,
            level="source",
            summary_text=summary.get("summary", ""),
            core_ideas=summary.get("core_ideas"),
            insights=summary.get("insights"),
            action_items=summary.get("action_items"),
            key_quotes=summary.get("key_quotes"),
            themes=summary.get("themes"),
            technical_concepts=summary.get("technical_concepts"),
            opportunities=summary.get("opportunities"),
            contradictions=summary.get("contradictions"),
            why_it_matters=summary.get("why_it_matters"),
            open_questions=summary.get("open_questions"),
            model_used=f"{cfg.llm.provider}/{_llm_model()}",
        )
        files.save_summary(source_id, json.dumps(summary, indent=2))
        db.update_source_status(source_id, "completed")

        reply = f"✅ *Analyzed!* (ID: `{source_id}`)\n\n📝 *Summary:*\n{summary.get('summary', '(empty)')[:1000]}"
        await msg.edit_text(reply, parse_mode="Markdown")

    except Exception:
        logger.exception("ingest_text error")
        if source_id:
            try:
                db.update_source_status(source_id, "failed")
            except Exception:
                logger.warning("could not mark source %s failed", source_id)
        await msg.edit_text("❌ Something went wrong. Check logs for details.")


async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    msg = await update.message.reply_text("📁 Processing file...")
    source_id = None
    try:
        attachment = update.message.document or update.message.audio or update.message.voice
        if attachment is None:
            await msg.edit_text("❌ Please send a PDF, audio, or text file.")
            return
        file = await attachment.get_file()
        if (file.file_size or 0) > MAX_UPLOAD_BYTES:
            await msg.edit_text(
                f"❌ File too large ({(file.file_size or 0) // (1024 * 1024)} MB). "
                f"Limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
            return
        ext = Path(file.file_path or "").suffix.lower() or ".bin"
        dest = DATA_DIR / "raw" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await file.download_to_drive(dest)

        is_audio_msg = update.message.audio is not None or update.message.voice is not None
        file_type = "pdf" if ext == ".pdf" else "audio" if (is_audio_msg or ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac")) else "text"
        title = update.message.document.file_name if update.message.document else f"audio{ext}"

        source_id = db.insert_source(file_type, title=title, file_path=str(dest), file_size=dest.stat().st_size)
        db.update_source_status(source_id, "processing")

        text = ""
        if file_type == "pdf":
            from app.extractors.pdf_extractor import extract_text

            extracted = extract_text(str(dest))
            text = extracted["text"]
            await msg.edit_text(f"📄 Extracted {len(text):,} chars\n🧠 Summarizing...")
        elif file_type == "audio":
            from app.transcription.transcriber import Transcriber

            t = Transcriber(cfg.transcription.model, cfg.transcription.device, cfg.transcription.compute_type)
            transcript = t.transcribe(str(dest))
            text = transcript["text"]
            db.insert_transcript(
                source_id,
                text=text,
                language=transcript["language"],
                duration_seconds=transcript.get("duration_seconds"),
                segments=transcript.get("segments", []),
                model_used=transcript.get("model_used", ""),
            )
            await msg.edit_text(f"🎤 Transcribed {len(text):,} chars\n🧠 Summarizing...")
        else:
            from app.extractors.text_extractor import extract_text as extract_txt

            extracted = extract_txt(str(dest))
            text = extracted["text"]
            await msg.edit_text(f"📝 Read {len(text):,} chars\n🧠 Summarizing...")

        if not text:
            raise RuntimeError("No text extracted from file")

        summary = pacex_summarize(text, title)
        db.insert_summary(
            source_id,
            level="source",
            summary_text=summary.get("summary", ""),
            core_ideas=summary.get("core_ideas"),
            insights=summary.get("insights"),
            action_items=summary.get("action_items"),
            key_quotes=summary.get("key_quotes"),
            themes=summary.get("themes"),
            technical_concepts=summary.get("technical_concepts"),
            opportunities=summary.get("opportunities"),
            contradictions=summary.get("contradictions"),
            why_it_matters=summary.get("why_it_matters"),
            open_questions=summary.get("open_questions"),
            model_used=f"{cfg.llm.provider}/{_llm_model()}",
        )
        files.save_summary(source_id, json.dumps(summary, indent=2))
        db.update_source_status(source_id, "completed")

        reply = f"✅ *{title[:60]}* (ID: `{source_id}`)\n\n📝 {summary.get('summary', '')[:1000]}"
        await msg.edit_text(reply, parse_mode="Markdown")

    except Exception:
        logger.exception("handle_file error")
        if source_id:
            try:
                db.update_source_status(source_id, "failed")
            except Exception:
                logger.warning("could not mark source %s failed", source_id)
        await msg.edit_text("❌ Something went wrong. Check logs for details.")


async def summary_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: `/summary <source_id>`", parse_mode="Markdown")
        return
    try:
        source_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Source ID must be a number")
        return

    src = db.get_source(source_id)
    if not src:
        await update.message.reply_text(f"Source `{source_id}` not found", parse_mode="Markdown")
        return

    summaries = db.get_source_summaries(source_id)
    if not summaries:
        await update.message.reply_text(f"No summary for `{source_id}` yet", parse_mode="Markdown")
        return

    s = summaries[0]
    lines = [
        f"📊 *{src['title'][:80]}*",
        f"Type: `{src['source_type']}` | ID: `{source_id}`",
        "",
        "📝 *Summary*",
        s.get("summary_text", "")[:1500],
    ]
    ideas = parse_json_field(s.get("core_ideas", "[]"))
    if ideas:
        lines.extend(["", "💡 *Core Ideas*"] + [f"• {i}" for i in ideas[:5]])
    actions = parse_json_field(s.get("action_items", "[]"))
    if actions:
        lines.extend(["", "✅ *Action Items*"] + [f"• {a}" for a in actions[:5]])
    why = s.get("why_it_matters", "")
    if why:
        lines.extend(["", f"🎯 *Why It Matters:* {why[:500]}"])
    if s.get("model_used"):
        lines.append(f"\n🤖 Model: `{s['model_used']}`")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def list_sources(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    sources = db.list_sources(limit=15)
    if not sources:
        await update.message.reply_text("No sources yet. Use `/ingest_youtube` or `/ingest_text`.")
        return

    lines = ["📋 *Recent Sources*\n"]
    for s in sources:
        icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
        icon = icons.get(s["status"], "❓")
        title = s.get("title", "Untitled")[:60]
        lines.append(f"{icon} `{s['id']}` — {title} ({s['source_type']})")
    lines.append("\nUse `/summary <id>` for details.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    msg = await update.message.reply_text("📊 Generating weekly report...")
    try:
        from app.reports.generator import ReportGenerator

        gen = ReportGenerator(db, files, llm, prompts)
        result = gen.generate_weekly()

        if result["status"] == "skipped":
            await msg.edit_text("No summaries found for this week. Ingest some content first.")
            return

        w_start, w_end = week_boundary()
        report_data = db.get_report(result["report_id"])
        if report_data:
            exec_summary = (report_data.get("executive_summary", "") or "")[:1500]
            await msg.edit_text(
                f"📊 *Weekly Report ({w_start} — {w_end})*\n\n"
                f"Sources: {result['source_count']}\n\n"
                f"{exec_summary}\n\n"
                f"Details: `/report`",
                parse_mode="Markdown",
            )
        else:
            await msg.edit_text("Report generated but no data found.")

    except Exception:
        logger.exception("report error")
        await msg.edit_text("❌ Something went wrong. Check logs for details.")


async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    query = " ".join(ctx.args)
    if not query:
        await update.message.reply_text("Usage: `/search <query>`", parse_mode="Markdown")
        return

    sources = db.list_sources()
    results = [s for s in sources if query.lower() in s.get("title", "").lower()]
    if not results:
        await update.message.reply_text(f"No sources matching `{query}`", parse_mode="Markdown")
        return

    lines = [f'📋 *Results for "{query}":*\n']
    for s in results[:10]:
        lines.append(f"`{s['id']}` — {s.get('title', 'Untitled')[:60]} ({s['source_type']})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def status_cmd(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    total = db.count_sources()
    completed = db.count_sources("completed")
    failed = db.count_sources("failed")
    reports_list = db.list_reports(limit=1)
    await update.message.reply_text(
        f"📡 *SignalForge Status*\n\n"
        f"Total sources: {total}\n"
        f"✅ Completed: {completed}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Reports: {len(reports_list)}\n"
        f"🤖 LLM: {cfg.llm.provider} ({_llm_model()})",
        parse_mode="Markdown",
    )


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return
    text = update.message.text.strip()
    from app.ingestion.youtube import find_youtube_url
    youtube_url = find_youtube_url(text)
    if youtube_url:
        ctx.args = [youtube_url]
        await ingest_youtube(update, ctx)
    elif len(text) > 200:
        ctx.args = [text]
        await ingest_text_cmd(update, ctx)
    else:
        response = _llm_chat(
            [{"role": "user", "content": text}],
            system_prompt=(
                "You are Hermes, the SignalForge research analyst — an elite research analyst "
                "and knowledge intelligence system. You are precise, analytical, and "
                "information-dense. You help the user ingest, analyze, and synthesize "
                "content from YouTube, PDFs, audio, and text using the PACE-X framework. "
                "Respond concisely with strong structure. Identify yourself as Hermes "
                "when asked who you are."
            ),
            temperature=0.5,
            max_tokens=500,
        )
        await update.message.reply_text(response)


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        return
    has_llm = (
        cfg.llm.gemini_api_key
        or cfg.llm.openrouter_api_key
        or cfg.llm.deepseek_api_key
        or cfg.llm.provider == "ollama"
    )
    if not has_llm:
        logger.error("No LLM configured: set GEMINI_API_KEY / OPENROUTER_API_KEY / DEEPSEEK_API_KEY, or LLM_PROVIDER=ollama")
        return
    if not ALLOWED_USERS and os.getenv("ALLOW_OPEN_BOT", "") != "1":
        logger.error("Refusing to start: ALLOWED_USERS is empty (open bot). Set ALLOWED_USERS=<your-telegram-id> or ALLOW_OPEN_BOT=1 for personal use.")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ingest_youtube", ingest_youtube))
    app.add_handler(CommandHandler("ingest_text", ingest_text_cmd))
    app.add_handler(CommandHandler("summary", summary_cmd))
    app.add_handler(CommandHandler("list", list_sources))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VOICE, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("SignalForge Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()


def validate_user_input(text: str | None, *, max_len: int = 4000) -> str:
    """Normalize and validate free-text user input from Telegram."""
    if text is None:
        raise ValueError("empty_input")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty_input")
    if len(cleaned) > max_len:
        raise ValueError("input_too_long")
    return cleaned


def categorize_error(exc: BaseException) -> str:
    """Map exceptions to stable categories for user-facing messages."""
    name = type(exc).__name__
    msg = str(exc).lower()
    if isinstance(exc, ValueError):
        if "empty" in msg:
            return "validation_empty"
        if "too_long" in msg or "too long" in msg:
            return "validation_length"
        return "validation"
    if isinstance(exc, TimeoutError) or "timeout" in msg:
        return "timeout"
    if isinstance(exc, ConnectionError) or "connection" in msg:
        return "network"
    if "rate" in msg and "limit" in msg:
        return "rate_limit"
    if name in {"HTTPError", "ApiError"}:
        return "api"
    return "unknown"
