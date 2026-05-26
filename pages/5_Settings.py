import streamlit as st
from pathlib import Path

from app.utils.config import load_config

cfg = load_config()

st.title("⚙️ Settings")
st.caption("Configure LLM provider, transcription, and system preferences.")

st.markdown("")
with st.container(border=True):
    st.subheader("🤖 LLM Configuration")
    provider = st.selectbox("Provider",
                            options=["openrouter", "ollama"],
                            index=0 if cfg.llm.provider == "openrouter" else 1,
                            help="OpenRouter for cloud LLMs, Ollama for local models")

    if provider == "openrouter":
        api_key = st.text_input("OpenRouter API Key",
                                 value=cfg.llm.openrouter_api_key or "",
                                 type="password",
                                 help="Get your key at openrouter.ai/keys")
        model = st.text_input("Model",
                              value=cfg.llm.openrouter_model,
                              help="e.g. google/gemini-2.0-flash-001, deepseek/deepseek-chat")
    else:
        base_url = st.text_input("Ollama Base URL",
                                  value=cfg.llm.ollama_base_url,
                                  help="Default: http://localhost:11434")
        model = st.text_input("Model",
                              value=cfg.llm.ollama_model,
                              help="e.g. llama3.2, mistral, qwen2.5")

with st.container(border=True):
    st.subheader("🎤 Transcription")
    model_size = st.selectbox("Whisper Model",
                               options=["tiny", "base", "small", "medium", "large-v3"],
                               index=0,
                               help="tiny=fastest, large-v3=most accurate")
    device = st.selectbox("Device", options=["cpu", "cuda"], index=0)
    compute_type = st.selectbox("Compute Type",
                                 options=["float32", "int8", "float16"],
                                 index=0)

with st.container(border=True):
    st.subheader("📐 Chunking")
    st.caption("Text is split into chunks before summarization. Larger chunks = fewer API calls.")
    max_chunk_size = st.slider("Max Chunk Size (characters)",
                                min_value=500, max_value=8000,
                                value=cfg.chunking.max_chunk_size, step=100)
    overlap = st.slider("Chunk Overlap (characters)",
                         min_value=0, max_value=1000,
                         value=cfg.chunking.overlap, step=50)

with st.container(border=True):
    st.subheader("☁️ Cloud Upload")
    remote = st.text_input("Rclone Remote Name", value=cfg.rclone.remote,
                           help="Name configured in rclone (e.g. 'mega')")
    remote_path = st.text_input("Remote Path", value=cfg.rclone.path,
                                help="Storage path on the remote")

st.divider()

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        st.success("Settings saved for this session.")
        st.info("Edit `.env` or `config.yaml` for permanent changes.")

st.divider()

with st.container(border=True):
    st.subheader("⚠️  Reset All Data")
    st.warning("This permanently deletes all sources, transcripts, summaries, reports, and uploaded files.")
    col1, col2 = st.columns([1, 3])
    confirm = col1.checkbox("I understand this is permanent", key="reset_confirm")
    if col2.button("🧹 Delete Everything", type="secondary", disabled=not confirm,
                   use_container_width=True):
        from database.schema import DB_PATH
        import shutil

        tables = ["report_sources", "source_tags", "tags", "reports",
                  "summaries", "transcripts", "sources"]
        db = st.session_state.db
        for table in tables:
            db._conn.execute(f"DELETE FROM {table}")
        db._conn.commit()

        data_dir = Path(st.session_state.config.app.data_dir)
        for sub in ["raw", "transcripts", "summaries", "markdown", "reports", "temp"]:
            sub_path = data_dir / sub
            if sub_path.exists():
                shutil.rmtree(sub_path)
                sub_path.mkdir(parents=True, exist_ok=True)

        log_file = Path(st.session_state.config.logging.file)
        if log_file.exists():
            try:
                log_file.unlink()
            except (PermissionError, OSError):
                pass

        st.success("All data cleared. Refreshing...")
        st.rerun()
