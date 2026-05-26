import streamlit as st
import json

from app.storage.db import Database
from app.utils.config import load_config
from app.utils.helpers import parse_json_field
from app.ui.components import render_source_card, render_summary

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "db" not in st.session_state:
    st.session_state.db = Database()

db: Database = st.session_state.db

st.title("🔍 Browse Sources")

status_filter = st.selectbox("Filter by status", ["all", "completed", "processing", "pending", "failed"])
sources = db.list_sources(status=None if status_filter == "all" else status_filter)

if not sources:
    st.info("No sources found.")
else:
    for src in sources:
        with st.expander(f"{src.get('title', 'Untitled')[:80]} ({src['source_type']})"):
            render_source_card(src)

            summaries = db.get_source_summaries(src["id"])
            if summaries:
                st.subheader("Summary")
                render_summary(summaries[0])

            transcript = db.get_transcript(src["id"])
            if transcript:
                with st.expander("View Full Transcript"):
                    st.text_area("Transcript", transcript["text"], height=300, key=f"t_{src['id']}")
