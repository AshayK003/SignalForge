import streamlit as st
from pathlib import Path

from app.utils.helpers import parse_json_field


def sidebar_nav():
    pages = {
        "Dashboard": "dashboard",
        "Ingest": "ingest",
        "Browse": "browse",
        "Reports": "reports",
        "Settings": "settings",
    }
    selection = st.sidebar.radio("Navigation", list(pages.keys()), key="nav")
    return pages[selection]


def status_badge(status: str) -> str:
    icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
    return f"{icons.get(status, '❓')} {status}"


def render_source_card(source: dict):
    with st.container():
        cols = st.columns([3, 1, 1])
        cols[0].write(f"**{source.get('title', 'Untitled')}**")
        cols[1].write(f"`{source.get('source_type', '?')}`")
        cols[2].write(status_badge(source.get("status", "unknown")))
        if source.get("url"):
            st.caption(f"🔗 {source['url']}")
        st.caption(f"🕐 {source.get('ingested_at', '')}")
        st.divider()


def render_summary(summary: dict, show_full: bool = True):
    st.markdown(summary.get("summary_text", "*No summary*"))

    if not show_full:
        return

    insights = parse_json_field(summary.get("insights", "[]"))
    actions = parse_json_field(summary.get("action_items", "[]"))
    quotes = parse_json_field(summary.get("key_quotes", "[]"))
    themes = parse_json_field(summary.get("themes", "[]"))
    opportunities = parse_json_field(summary.get("opportunities", "[]"))

    if themes:
        st.subheader("Themes")
        for t in themes:
            st.markdown(f"- {t}")

    if insights:
        st.subheader("Insights")
        for i in insights:
            st.markdown(f"- {i}")

    if actions:
        st.subheader("Action Items")
        for a in actions:
            st.markdown(f"- [ ] {a}")

    if quotes:
        st.subheader("Key Quotes")
        for q in quotes:
            st.markdown(f"> {q}")

    if opportunities:
        st.subheader("Opportunities")
        for o in opportunities:
            name = o.get("opportunity", str(o)) if isinstance(o, dict) else str(o)
            why = o.get("why", "") if isinstance(o, dict) else ""
            st.markdown(f"- **{name}**")
            if why:
                st.caption(f"  {why}")
