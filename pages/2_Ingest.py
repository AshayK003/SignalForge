import streamlit as st
import json
from pathlib import Path

from app.storage.db import Database
from app.storage.files import FileManager
from app.utils.config import load_config
from app.utils.logging import setup_logging

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "db" not in st.session_state:
    st.session_state.db = Database()
if "files" not in st.session_state:
    st.session_state.files = FileManager(st.session_state.config.app.data_dir)

cfg = st.session_state.config
db: Database = st.session_state.db
files: FileManager = st.session_state.files
logger = setup_logging(cfg.logging.level, cfg.logging.file)

st.title("📥 Ingest Content")
st.caption("Add YouTube videos or files to process through the intelligence pipeline.")

tab1, tab2 = st.tabs(["🎬 YouTube URL", "📁 File Upload"])

with tab1:
    with st.container(border=True):
        st.markdown("**Download YouTube videos, transcribe them, and generate AI summaries.**")
        with st.form("youtube_form", clear_on_submit=True):
            urls_text = st.text_area(
                "YouTube URLs (one per line)",
                placeholder="https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...",
                help="Paste one or more YouTube video links, one per line.",
            )
            submitted = st.form_submit_button("🚀 Process Videos", type="primary", use_container_width=True)

    if submitted and urls_text:
        import concurrent.futures
        import threading
        from datetime import datetime

        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        files.clean_temp()

        # Phase 1: fetch transcripts (sequential)
        video_data = []
        phase1_progress = st.progress(0, text="Fetching transcripts...")
        for idx, url in enumerate(urls):
            source_id = None
            with st.status(f"📥 Video {idx+1}/{len(urls)}", expanded=True) as status:
                try:
                    from app.ingestion.youtube import get_captions, download_audio

                    st.write(f"🔗 {url}")
                    st.write("📝 Checking for captions...")
                    caption_result = get_captions(url, files.temp, logger)

                    if caption_result:
                        text = caption_result["text"]
                        transcript = {
                            "text": text,
                            "language": "en",
                            "duration_seconds": caption_result.get("duration_seconds"),
                            "segments": [],
                            "model_used": "youtube-captions",
                        }
                        result = caption_result
                        st.write(f"✅ Captions — {len(text):,} chars")
                    else:
                        st.write("⬇️ No captions — downloading audio...")
                        result = download_audio(url, files.temp, logger)
                        audio_path = result.get("audio_path", "")
                        if not audio_path or not Path(audio_path).exists():
                            raise RuntimeError(
                                f"Audio download failed — yt-dlp did not produce an output file. "
                                f"The video may be blocked from downloading."
                            )
                        duration = result.get("duration_seconds", 0)
                        st.write(f"🎤 Transcribing ({duration//60}m {duration%60}s)...")
                        from app.transcription.transcriber import Transcriber
                        t = Transcriber(cfg.transcription.model, cfg.transcription.device,
                                        cfg.transcription.compute_type, logger)
                        transcript = t.transcribe(audio_path)
                        st.write(f"✅ Transcribed — {len(transcript['text']):,} chars")

                    source_id = db.insert_source(
                        source_type="youtube",
                        title=result["title"],
                        url=result["url"],
                        file_path=result.get("audio_path", ""),
                        metadata={"method": result.get("method", "unknown"), "video_id": result.get("video_id", "")},
                    )
                    db.update_source_status(source_id, "processing")
                    files.save_transcript(source_id, transcript["text"], "txt")
                    db.insert_transcript(
                        source_id=source_id,
                        text=transcript["text"],
                        language=transcript.get("language", "en"),
                        duration_seconds=transcript.get("duration_seconds"),
                        segments=transcript.get("segments", []),
                        model_used=transcript.get("model_used", "youtube-captions"),
                    )

                    status.update(label=f"✅ **Fetched:** {result['title']}", state="complete")
                    video_data.append({
                        "idx": idx,
                        "url": url,
                        "title": result["title"],
                        "source_id": source_id,
                        "transcript_text": transcript["text"],
                        "result": result,
                    })
                except Exception as e:
                    if source_id is not None:
                        db.update_source_status(source_id, "failed", str(e))
                    status.update(label=f"❌ **Skipped:** {url}", state="error")
                    st.error(f"Error: {e}")

            phase1_progress.progress((idx + 1) / len(urls),
                                     text=f"Fetched {idx+1}/{len(urls)}")

        # Phase 2: summarize all in parallel
        if video_data:
            st.subheader("🧠 Summarizing all videos in parallel...")
            from app.summarization.llm_client import LLMClient
            from app.summarization.prompts import PromptLibrary
            from app.summarization.pipeline import SummarizationPipeline

            llm = LLMClient(cfg, logger)
            prompts = PromptLibrary()
            pipeline = SummarizationPipeline(llm, prompts, logger)

            summaries = [None] * len(video_data)
            phase2_progress = st.progress(0, text="Summarizing...")
            phase2_lock = threading.Lock()
            phase2_done = 0

            def summarize_one(video):
                pipe = SummarizationPipeline(llm, prompts, logger)
                summary = pipe.process_structured(
                    video["transcript_text"],
                    source_title=video["title"],
                    max_chunk_size=cfg.chunking.max_chunk_size,
                    overlap=cfg.chunking.overlap,
                )
                summary["source_id"] = video["source_id"]
                summary["title"] = video["title"]
                return video["idx"], summary

            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(video_data), 5)) as executor:
                futures = {executor.submit(summarize_one, v): v for v in video_data}
                for future in concurrent.futures.as_completed(futures):
                    vidx, summary = future.result()
                    summaries[vidx] = summary
                    sid = summary["source_id"]
                    db.insert_summary(
                        source_id=sid,
                        level="source",
                        summary_text=summary.get("summary", ""),
                        core_ideas=summary.get("core_ideas", []),
                        insights=summary.get("insights", []),
                        action_items=summary.get("action_items", []),
                        key_quotes=summary.get("key_quotes", []),
                        themes=summary.get("themes", []),
                        technical_concepts=summary.get("technical_concepts", []),
                        opportunities=summary.get("opportunities", []),
                        contradictions=summary.get("contradictions", []),
                        why_it_matters=summary.get("why_it_matters", ""),
                        open_questions=summary.get("open_questions", []),
                        model_used=cfg.llm.openrouter_model if cfg.llm.provider == "openrouter" else cfg.llm.ollama_model,
                    )
                    files.save_summary(sid, json.dumps(summary, indent=2))
                    db.update_source_status(sid, "completed")
                    with phase2_lock:
                        phase2_done += 1
                    phase2_progress.progress(
                        phase2_done / len(video_data),
                        text=f"Summarized {phase2_done}/{len(video_data)}")

            # Phase 3: combine all summaries into one
            st.subheader("🔗 Generating combined synthesis...")
            sources_text = "\n\n".join(
                f"Source: {s['title']}\nSummary: {s.get('summary', '')}"
                for s in summaries
            )
            combined_prompt = prompts.render(
                "weekly_report",
                sources=sources_text,
                week_start=datetime.now().strftime("%Y-%m-%d"),
                week_end=datetime.now().strftime("%Y-%m-%d"),
                source_count=len(summaries),
            )
            combined = llm.chat([
                {"role": "system",
                 "content": "You are a synthesis analyst. Combine these source summaries into a cohesive analysis."},
                {"role": "user", "content": combined_prompt},
            ])

            with st.container(border=True):
                st.markdown("### 📊 Combined Synthesis")
                st.markdown(combined)

            success_count = len(video_data)
            fail_count = len(urls) - success_count
            if fail_count == 0:
                st.success(f"✅ All {success_count} videos processed.")
            else:
                st.warning(f"⚠️ {success_count} succeeded, {fail_count} failed.")
        else:
            st.error("No videos could be processed.")

with tab2:
    with st.container(border=True):
        st.markdown("**Upload a PDF, text file, or audio file for processing.**")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "md", "mp3", "wav", "m4a", "ogg", "flac"],
            help="Supported: PDF, TXT, MD, MP3, WAV, M4A, OGG, FLAC",
        )

    if uploaded_file:
        source_id = None
        with st.status("Processing file...", expanded=True) as status:
            try:
                from app.ingestion.files import classify_file

                file_path = files.save_upload(uploaded_file, uploaded_file.name)
                file_type = classify_file(uploaded_file.name)
                file_size = file_path.stat().st_size

                st.write(f"📁 **Type detected:** `{file_type}` ({uploaded_file.name})")

                source_id = db.insert_source(
                    source_type=file_type,
                    title=uploaded_file.name,
                    file_path=str(file_path),
                    file_size=file_size,
                )
                db.update_source_status(source_id, "processing")

                text = ""

                if file_type == "pdf":
                    st.write("📄 **Extracting PDF text...**")
                    from app.extractors.pdf_extractor import extract_text
                    extracted = extract_text(str(file_path), logger=logger)
                    text = extracted["text"]
                    st.write(f"✅ **Extracted** — {len(text):,} chars across {extracted['page_count']} pages")
                elif file_type == "text":
                    st.write("📝 **Reading text file...**")
                    from app.extractors.text_extractor import extract_text as extract_text_file
                    extracted = extract_text_file(str(file_path))
                    text = extracted["text"]
                    st.write(f"✅ **Read** — {len(text):,} chars")
                elif file_type == "audio":
                    st.write("🎤 **Transcribing audio...**")
                    from app.transcription.transcriber import Transcriber
                    t = Transcriber(cfg.transcription.model, cfg.transcription.device,
                                    cfg.transcription.compute_type, logger)
                    transcript = t.transcribe(str(file_path))
                    t.save_transcript(transcript, files.transcripts, source_id)
                    text = transcript["text"]
                    st.write(f"✅ **Transcription complete** — {len(text):,} chars")
                    db.insert_transcript(
                        source_id=source_id,
                        text=text,
                        language=transcript["language"],
                        duration_seconds=transcript["duration_seconds"],
                        segments=transcript["segments"],
                        model_used=transcript["model_used"],
                    )

                if text:
                    st.write("🧠 **Summarizing with PACE-X AI...**")
                    from app.summarization.llm_client import LLMClient
                    from app.summarization.prompts import PromptLibrary
                    from app.summarization.pipeline import SummarizationPipeline

                    llm = LLMClient(cfg, logger)
                    prompts = PromptLibrary()
                    pipeline = SummarizationPipeline(llm, prompts, logger)
                    summary = pipeline.process_structured(
                        text,
                        source_title=uploaded_file.name,
                        max_chunk_size=cfg.chunking.max_chunk_size,
                        overlap=cfg.chunking.overlap,
                    )

                    db.insert_summary(
                        source_id=source_id,
                        level="source",
                        summary_text=summary.get("summary", ""),
                        core_ideas=summary.get("core_ideas", []),
                        insights=summary.get("insights", []),
                        action_items=summary.get("action_items", []),
                        key_quotes=summary.get("key_quotes", []),
                        themes=summary.get("themes", []),
                        technical_concepts=summary.get("technical_concepts", []),
                        opportunities=summary.get("opportunities", []),
                        contradictions=summary.get("contradictions", []),
                        why_it_matters=summary.get("why_it_matters", ""),
                        open_questions=summary.get("open_questions", []),
                        model_used=cfg.llm.openrouter_model if cfg.llm.provider == "openrouter" else cfg.llm.ollama_model,
                    )
                    files.save_summary(source_id, json.dumps(summary, indent=2))
                    st.write("✅ **Summary generated**")

                db.update_source_status(source_id, "completed")
                status.update(label="✅ **Processing complete!**", state="complete")
                st.success(f"Processed: **{uploaded_file.name}**")

            except Exception as e:
                if source_id is not None:
                    db.update_source_status(source_id, "failed", str(e))
                status.update(label="❌ **Processing failed**", state="error")
                st.error(f"Error: {e}")
