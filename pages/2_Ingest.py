import streamlit as st
import json
from pathlib import Path

from app.storage.db import Database
from app.storage.files import FileManager
from app.utils.config import load_config
from app.utils.helpers import ensure_dir
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

tab1, tab2 = st.tabs(["YouTube URL", "File Upload"])

with tab1:
    with st.form("youtube_form"):
        url = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...")
        submitted = st.form_submit_button("Download & Process", type="primary")

    if submitted and url:
        with st.status("Processing YouTube video...", expanded=True) as status:
            try:
                st.write("⬇️ Downloading audio...")
                from app.ingestion.youtube import download_audio
                result = download_audio(url, files.temp, logger)

                source_id = db.insert_source(
                    source_type="youtube",
                    title=result["title"],
                    url=result["url"],
                    file_path=result["audio_path"],
                    metadata=result["metadata"],
                )
                db.update_source_status(source_id, "processing")

                st.write(f"🎤 Transcribing audio ({result.get('duration_seconds', 0)}s)...")
                from app.transcription.transcriber import Transcriber
                t = Transcriber(cfg.transcription.model, cfg.transcription.device,
                                cfg.transcription.compute_type, logger)
                transcript = t.transcribe(result["audio_path"])
                t.save_transcript(transcript, files.transcripts, source_id)
                db.insert_transcript(
                    source_id=source_id,
                    text=transcript["text"],
                    language=transcript["language"],
                    duration_seconds=transcript["duration_seconds"],
                    segments=transcript["segments"],
                    model_used=transcript["model_used"],
                )

                st.write("🧠 Summarizing...")
                from app.summarization.llm_client import LLMClient
                from app.summarization.prompts import PromptLibrary
                from app.summarization.pipeline import SummarizationPipeline

                llm = LLMClient(cfg, logger)
                prompts = PromptLibrary()
                pipeline = SummarizationPipeline(llm, prompts, logger)
                summary = pipeline.process_structured(
                    transcript["text"],
                    source_title=result["title"],
                    max_chunk_size=cfg.chunking.max_chunk_size,
                    overlap=cfg.chunking.overlap,
                )

                db.insert_summary(
                    source_id=source_id,
                    level="source",
                    summary_text=summary.get("summary", ""),
                    insights=summary.get("insights", []),
                    action_items=summary.get("action_items", []),
                    key_quotes=summary.get("key_quotes", []),
                    themes=summary.get("themes", []),
                    technical_concepts=summary.get("technical_concepts", []),
                    opportunities=summary.get("opportunities", []),
                    contradictions=summary.get("contradictions", []),
                    model_used=cfg.llm.openrouter_model if cfg.llm.provider == "openrouter" else cfg.llm.ollama_model,
                )

                files.save_summary(source_id, json.dumps(summary, indent=2))
                db.update_source_status(source_id, "completed")

                status.update(label="✅ Processing complete!", state="complete")
                st.success(f"Processed: {result['title']}")

            except Exception as e:
                db.update_source_status(source_id if 'source_id' in dir() else 0, "failed", str(e))
                status.update(label="❌ Processing failed", state="error")
                st.error(f"Error: {e}")

with tab2:
    uploaded_file = st.file_uploader(
        "Upload a file",
        type=["pdf", "txt", "md", "mp3", "wav", "m4a", "ogg", "flac"],
    )

    if uploaded_file:
        with st.status("Processing file...", expanded=True) as status:
            try:
                from app.ingestion.files import classify_file

                file_info = files.save_upload(uploaded_file, uploaded_file.name)
                file_type = classify_file(uploaded_file.name)

                source_id = db.insert_source(
                    source_type=file_type,
                    title=uploaded_file.name,
                    file_path=file_info["file_path"],
                    file_size=file_info["file_size"],
                )
                db.update_source_status(source_id, "processing")

                text = ""

                if file_type == "pdf":
                    st.write("📄 Extracting PDF text...")
                    from app.extractors.pdf_extractor import extract_text
                    extracted = extract_text(file_info["file_path"], logger=logger)
                    text = extracted["text"]
                elif file_type == "text":
                    st.write("📝 Reading text file...")
                    from app.extractors.text_extractor import extract_text as extract_text_file
                    extracted = extract_text_file(file_info["file_path"])
                    text = extracted["text"]
                elif file_type == "audio":
                    st.write("🎤 Transcribing audio...")
                    from app.transcription.transcriber import Transcriber
                    t = Transcriber(cfg.transcription.model, cfg.transcription.device,
                                    cfg.transcription.compute_type, logger)
                    transcript = t.transcribe(file_info["file_path"])
                    t.save_transcript(transcript, files.transcripts, source_id)
                    text = transcript["text"]
                    db.insert_transcript(
                        source_id=source_id,
                        text=text,
                        language=transcript["language"],
                        duration_seconds=transcript["duration_seconds"],
                        segments=transcript["segments"],
                        model_used=transcript["model_used"],
                    )

                if text:
                    st.write("🧠 Summarizing...")
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
                        insights=summary.get("insights", []),
                        action_items=summary.get("action_items", []),
                        key_quotes=summary.get("key_quotes", []),
                        themes=summary.get("themes", []),
                        technical_concepts=summary.get("technical_concepts", []),
                        opportunities=summary.get("opportunities", []),
                        contradictions=summary.get("contradictions", []),
                        model_used=cfg.llm.openrouter_model if cfg.llm.provider == "openrouter" else cfg.llm.ollama_model,
                    )
                    files.save_summary(source_id, json.dumps(summary, indent=2))

                db.update_source_status(source_id, "completed")
                status.update(label="✅ Processing complete!", state="complete")
                st.success(f"Processed: {uploaded_file.name}")

            except Exception as e:
                if 'source_id' in dir():
                    db.update_source_status(source_id, "failed", str(e))
                status.update(label="❌ Processing failed", state="error")
                st.error(f"Error: {e}")
