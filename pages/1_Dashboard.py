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
col1.metric("Total Sources", db.count_sources(), border=True)
col2.metric("Completed", db.count_sources("completed"), border=True)
col3.metric("Processing", db.count_sources("processing"), border=True)
col4.metric("Failed", db.count_sources("failed"), border=True)

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Recent Activity")
    recent = db.list_sources(limit=10)
    if recent:
        for src in recent:
            icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
            with st.container(border=True):
                cols = st.columns([4, 1, 1, 1])
                cols[0].markdown(f"**{src.get('title', 'Untitled')[:80]}**")
                cols[1].markdown(f"`{src['source_type']}`")
                cols[2].markdown(f"🕐 {src['ingested_at'][:10]}")
                cols[3].markdown(icons.get(src["status"], "❓"))
    else:
        st.info("No sources yet. Go to **Ingest** to add content.")

with col_right:
    st.subheader("Quick Actions")
    if st.button("📥 Go to Ingest", use_container_width=True):
        st.switch_page("pages/2_Ingest.py")
    if st.button("📊 Go to Reports", use_container_width=True):
        st.switch_page("pages/4_Reports.py")
    if st.button("🔍 Browse Sources", use_container_width=True):
        st.switch_page("pages/3_Browse.py")

    st.divider()
    st.subheader("Summary Stats")
    total = db.count_sources()
    if total > 0:
        completed = db.count_sources("completed")
        failed = db.count_sources("failed")
        st.metric("Success Rate", f"{completed/max(total,1)*100:.0f}%",
                  delta=f"{completed}/{total}")
        reports = db.list_reports(limit=1)
        if reports:
            st.metric("Latest Report", reports[0]["week_start"])
        else:
            st.write("No reports yet")
