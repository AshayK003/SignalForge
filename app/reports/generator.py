from datetime import datetime, timedelta
from typing import Any

from app.reports.md_gen import generate_markdown
from app.reports.pdf_gen import generate_pdf
from app.storage.db import Database
from app.storage.files import FileManager
from app.summarization.llm_client import LLMClient
from app.summarization.prompts import PromptLibrary
from app.utils.helpers import parse_json_field, week_boundary


class ReportGenerator:
    def __init__(self, db: Database, files: FileManager, llm: LLMClient,
                 prompts: PromptLibrary, logger: Any = None):
        self.db = db
        self.files = files
        self.llm = llm
        self.prompts = prompts
        self.log = logger

    def generate_weekly(self, week_start: str | None = None,
                        week_end: str | None = None) -> dict:
        if not week_start or not week_end:
            week_start, week_end = week_boundary()

        summaries = self.db.get_summaries_in_week(week_start, week_end)

        if not summaries:
            if self.log:
                self.log(f"No summaries found for week {week_start} to {week_end}")
            return {"status": "skipped", "reason": "no_summaries"}

        source_ids = list(set(s["source_id"] for s in summaries))

        sources_text = []
        all_insights = []
        all_action_items = []
        all_quotes = []
        all_themes = set()
        all_opportunities = []
        all_contradictions = []

        for s in summaries:
            src = self.db.get_source(s["source_id"])
            title = src["title"] if src else "Unknown"
            sources_text.append(f"Source: {title}\n{s['summary_text']}")
            all_insights.extend(parse_json_field(s.get("insights", "[]")) or [])
            all_action_items.extend(parse_json_field(s.get("action_items", "[]")) or [])
            all_quotes.extend(parse_json_field(s.get("key_quotes", "[]")) or [])
            for t in (parse_json_field(s.get("themes", "[]")) or []):
                all_themes.add(t)
            all_opportunities.extend(parse_json_field(s.get("opportunities", "[]")) or [])
            all_contradictions.extend(parse_json_field(s.get("contradictions", "[]")) or [])

        combined = "\n\n".join(sources_text)

        report_prompt = self.prompts.render(
            "weekly_report",
            sources=combined,
            week_start=week_start,
            week_end=week_end,
            source_count=len(source_ids),
        )

        executive_summary = self.llm.chat([
            {"role": "system", "content": "You are an executive intelligence analyst. Write a comprehensive weekly report."},
            {"role": "user", "content": report_prompt},
        ])

        week_title = f"Weekly Intelligence Report: {week_start} to {week_end}"

        content = generate_markdown(
            title=week_title,
            week_start=week_start,
            week_end=week_end,
            executive_summary=executive_summary,
            source_count=len(source_ids),
            insights=all_insights,
            action_items=all_action_items,
            quotes=all_quotes,
            themes=list(all_themes),
            opportunities=all_opportunities,
            contradictions=all_contradictions,
            sources=[self.db.get_source(sid) for sid in source_ids],
        )

        md_path = self.files.save_report(
            f"report_{week_start}_{week_end}", content, "md"
        )

        pdf_data = generate_pdf(
            title=week_title,
            week_start=week_start,
            week_end=week_end,
            executive_summary=executive_summary,
            source_count=len(source_ids),
            insights=all_insights,
            action_items=all_action_items,
            quotes=all_quotes,
            themes=list(all_themes),
            opportunities=all_opportunities,
            contradictions=all_contradictions,
        )

        pdf_path = self.files.save_report(
            f"report_{week_start}_{week_end}", pdf_data, "pdf"
        )

        report_id = self.db.insert_report(
            week_start=week_start,
            week_end=week_end,
            title=week_title,
            executive_summary=executive_summary,
            source_count=len(source_ids),
            local_pdf_path=str(pdf_path),
            local_md_path=str(md_path),
        )

        for sid in source_ids:
            self.db.add_report_source(report_id, sid)

        if self.log:
            self.log(f"Weekly report generated: {week_start} to {week_end}, {len(source_ids)} sources")

        return {
            "status": "created",
            "report_id": report_id,
            "pdf_path": str(pdf_path),
            "md_path": str(md_path),
            "source_count": len(source_ids),
        }
