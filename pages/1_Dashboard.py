import streamlit as st

st.set_page_config(page_title="SignalForge", page_icon="📡", layout="wide")

from app.storage.db import Database
from app.utils.config import load_config

if "db" not in st.session_state:
    cfg = load_config()
    st.session_state.config = cfg
    st.session_state.db = Database()

db: Database = st.session_state.db

st.title("📡 SignalForge")
st.caption("Local-first AI knowledge digest system")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sources", db.count_sources())
col2.metric("Completed", db.count_sources("completed"))
col3.metric("Processing", db.count_sources("processing"))
col4.metric("Failed", db.count_sources("failed"))

st.subheader("Recent Activity")
recent = db.list_sources(limit=10)
if recent:
    for src in recent:
        c = st.columns([3, 1, 1, 1])
        c[0].write(src.get("title", "Untitled")[:60])
        c[1].write(f"`{src['source_type']}`")
        c[2].write(f"🕐 {src['ingested_at'][:10]}")
        icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
        c[3].write(icons.get(src["status"], "❓"))
else:
    st.info("No sources yet. Go to **Ingest** to add content.")
