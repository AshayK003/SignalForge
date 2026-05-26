import streamlit as st

from app.utils.helpers import parse_json_field


def status_badge(status: str) -> str:
    icons = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}
    return f"{icons.get(status, '❓')} {status}"


def render_source_card(source: dict):
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

    core_ideas = parse_json_field(summary.get("core_ideas", "[]"))
    insights = parse_json_field(summary.get("insights", "[]"))
    actions = parse_json_field(summary.get("action_items", "[]"))
    quotes = parse_json_field(summary.get("key_quotes", "[]"))
    themes = parse_json_field(summary.get("themes", "[]"))
    opportunities = parse_json_field(summary.get("opportunities", "[]"))
    contradictions = parse_json_field(summary.get("contradictions", "[]"))
    why_it_matters = summary.get("why_it_matters", "")
    open_questions = parse_json_field(summary.get("open_questions", "[]"))

    if core_ideas:
        with st.container(border=True):
            st.markdown("**💡 Core Ideas**")
            for idea in core_ideas:
                st.markdown(f"- {idea}")

    if themes:
        with st.container(border=True):
            st.markdown("**🏷️ Themes**")
            st.markdown(" ".join(f"`{t}`" for t in themes))

    if insights:
        with st.container(border=True):
            st.markdown("**🔍 Insights**")
            for i in insights:
                st.markdown(f"- {i}")

    if contradictions:
        with st.container(border=True):
            st.markdown("**⚡ Contrarian / Surprising Points**")
            for c in contradictions:
                st.markdown(f"- {c}")

    if actions:
        with st.container(border=True):
            st.markdown("**✅ Actionable Takeaways**")
            for a in actions:
                st.markdown(f"- [ ] {a}")

    if quotes:
        with st.container(border=True):
            st.markdown("**💬 Key Quotes**")
            for q in quotes:
                st.markdown(f"> *{q}*")

    if opportunities:
        with st.container(border=True):
            st.markdown("**🚀 Opportunities**")
            for o in opportunities:
                text = o.get("opportunity", str(o)) if isinstance(o, dict) else str(o)
                st.markdown(f"- **{text}**")

    if why_it_matters:
        with st.container(border=True):
            st.markdown("**🎯 Why This Matters**")
            st.markdown(why_it_matters)

    if open_questions:
        with st.container(border=True):
            st.markdown("**❓ Open Questions**")
            for q in open_questions:
                st.markdown(f"- {q}")
