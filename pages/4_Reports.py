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
st.caption("Generate and download weekly intelligence reports.")

st.divider()

col1, col2 = st.columns([3, 1])

with col1:
    reports = db.list_reports()
    st.metric("Total Reports", len(reports))

with col2:
    st.subheader("Generate")
    if st.button("📄 Generate This Week", type="primary", use_container_width=True):
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
                    st.rerun()

            except Exception as e:
                st.error(f"Report generation failed: {e}")

if not reports:
    st.info("No reports yet. Generate your first weekly report.")
else:
    st.divider()
    for report in reports:
        rid = report["id"]
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].markdown(f"**{report['week_start']} → {report['week_end']}**")
            cols[1].metric("Sources", report["source_count"], border=False)
            cols[2].write(f"📅 {report['created_at'][:10]}")

            has_pdf = report.get("local_pdf_path") and Path(report["local_pdf_path"]).exists()
            has_md = report.get("local_md_path") and Path(report["local_md_path"]).exists()

            if has_pdf:
                with open(report["local_pdf_path"], "rb") as f:
                    cols[3].download_button("📄 PDF", f,
                        file_name=Path(report["local_pdf_path"]).name,
                        mime="application/pdf", key=f"pdf_{rid}",
                        use_container_width=True)

            if has_md:
                md_content = Path(report["local_md_path"]).read_text(encoding="utf-8")
                cols[4].download_button("📝 MD", md_content,
                    file_name=Path(report["local_md_path"]).name,
                    mime="text/markdown", key=f"md_{rid}",
                    use_container_width=True)

            if report.get("executive_summary"):
                with st.expander("📋 View Executive Summary"):
                    st.markdown(report["executive_summary"])
