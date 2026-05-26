import streamlit as st
import os
from pathlib import Path

from app.utils.config import load_config, Config
from app.utils.logging import setup_logging

cfg = load_config()

st.title("⚙️ Settings")

with st.expander("LLM Configuration", expanded=True):
    provider = st.selectbox("Provider", ["openrouter", "ollama"],
                            index=0 if cfg.llm.provider == "openrouter" else 1)

    if provider == "openrouter":
        api_key = st.text_input("OpenRouter API Key",
                                 value=cfg.llm.openrouter_api_key or "",
                                 type="password")
        model = st.text_input("Model", value=cfg.llm.openrouter_model)
        st.info("Models: google/gemini-2.0-flash-001, deepseek/deepseek-chat, qwen/qwen-2.5-72b")
    else:
        base_url = st.text_input("Ollama Base URL", value=cfg.llm.ollama_base_url)
        model = st.text_input("Model", value=cfg.llm.ollama_model)

with st.expander("Transcription"):
    model_size = st.selectbox("Whisper Model Size",
                               ["tiny", "base", "small", "medium", "large-v3"],
                               index=1)
    device = st.selectbox("Device", ["auto", "cpu", "cuda"], index=0)
    compute_type = st.selectbox("Compute Type", ["int8", "float16", "float32"], index=0)

with st.expander("Chunking"):
    max_chunk_size = st.slider("Max Chunk Size (chars)", 500, 8000, cfg.chunking.max_chunk_size, step=100)
    overlap = st.slider("Chunk Overlap (chars)", 0, 1000, cfg.chunking.overlap, step=50)

with st.expander("Cloud Upload (rclone)"):
    remote = st.text_input("Rclone Remote Name", value=cfg.rclone.remote)
    remote_path = st.text_input("Remote Path", value=cfg.rclone.path)

if st.button("Save Settings", type="primary"):
    st.success("Settings saved to session (env vars for persistence). "
               "Edit .env or config.yaml for permanent changes.")
    st.info("Settings apply on next processing run.")
