import streamlit as st

from app.storage.db import Database
from app.utils.config import load_config
from app.ui.components import render_summary

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "db" not in st.session_state:
    st.session_state.db = Database()

db: Database = st.session_state.db

st.title("🔍 Browse Sources")
st.caption("View all ingested content, transcripts, and AI-generated summaries.")

col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("🔎 Search by title", placeholder="Type to filter...")
with col2:
    status_filter = st.selectbox("Status", ["all", "completed", "processing", "pending", "failed"],
                                 label_visibility="collapsed")

sources = db.list_sources(status=None if status_filter == "all" else status_filter)
if search:
    sources = [s for s in sources if search.lower() in s.get("title", "").lower()]

if not sources:
    st.info("No sources found. Go to **Ingest** to add content.")
else:
    st.caption(f"Showing {len(sources)} source(s)")

    for src in sources:
        icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
        status_icon = icons.get(src["status"], "❓")
        label = f"{status_icon} **{src.get('title', 'Untitled')[:100]}** — `{src['source_type']}` — {src['ingested_at'][:10]}"

        with st.expander(label):
            meta_cols = st.columns([3, 1, 1])
            with meta_cols[0]:
                if src.get("url"):
                    st.markdown(f"🔗 [{src['url']}]({src['url']})")
                st.caption(f"**Status:** {src['status']}  |  **Type:** {src['source_type']}")
            with meta_cols[1]:
                st.caption(f"**Ingested:** {src['ingested_at']}")
            with meta_cols[2]:
                if src.get("file_size"):
                    size = src["file_size"]
                    if size > 1_000_000:
                        st.caption(f"**Size:** {size/1_000_000:.1f} MB")
                    else:
                        st.caption(f"**Size:** {size//1024} KB")
            st.divider()

            summaries = db.get_source_summaries(src["id"])
            if summaries:
                render_summary(summaries[0])

            transcript = db.get_transcript(src["id"])
            if transcript:
                with st.expander("📄 View Full Transcript"):
                    st.text_area("Transcript", transcript["text"],
                                 height=300, key=f"t_{src['id']}")
