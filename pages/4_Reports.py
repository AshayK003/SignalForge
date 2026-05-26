import streamlit as st
from pathlib import Path

from app.storage.db import Database
from app.utils.config import load_config

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "db" not in st.session_state:
    st.session_state.db = Database()

cfg = st.session_state.config
db: Database = st.session_state.db

st.title("📊 Weekly Reports")

col1, col2 = st.columns([3, 1])

with col2:
    st.subheader("Generate Report")
    if st.button("Generate This Week's Report", type="primary", use_container_width=True):
        with st.status("Generating weekly report...") as status:
            try:
                from app.storage.files import FileManager
                from app.summarization.llm_client import LLMClient
                from app.summarization.prompts import PromptLibrary
                from app.reports.generator import ReportGenerator
                from app.utils.logging import setup_logging

                logger = setup_logging(cfg.logging.level, cfg.logging.file)
                files = FileManager(cfg.app.data_dir)
                llm = LLMClient(cfg, logger)
                prompts = PromptLibrary()
                gen = ReportGenerator(db, files, llm, prompts, logger)
                result = gen.generate_weekly()

                if result["status"] == "skipped":
                    st.warning("No summaries found for this week. Ingest some content first.")
                else:
                    st.success(f"Report generated! {result['source_count']} sources included.")
                    st.session_state["last_report"] = result

            except Exception as e:
                st.error(f"Report generation failed: {e}")

reports = db.list_reports()

if not reports:
    st.info("No reports yet. Generate your first weekly report.")
else:
    for report in reports:
        with st.expander(f"{report['week_start']} to {report['week_end']} — {report.get('title', 'Untitled')[:60]}"):
            c = st.columns([1, 1, 2])
            c[0].metric("Sources", report["source_count"])
            c[1].write(f"Created: {report['created_at'][:10]}")

            if report.get("local_pdf_path") and Path(report["local_pdf_path"]).exists():
                with open(report["local_pdf_path"], "rb") as f:
                    c[2].download_button(
                        "📄 Download PDF",
                        f,
                        file_name=Path(report["local_pdf_path"]).name,
                        mime="application/pdf",
                    )

            if report.get("local_md_path") and Path(report["local_md_path"]).exists():
                md_content = Path(report["local_md_path"]).read_text(encoding="utf-8")
                c[2].download_button(
                    "📝 Download Markdown",
                    md_content,
                    file_name=Path(report["local_md_path"]).name,
                    mime="text/markdown",
                )

            if report.get("executive_summary"):
                st.subheader("Executive Summary")
                st.markdown(report["executive_summary"])
