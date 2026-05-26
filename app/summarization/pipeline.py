import json
import re
from typing import Any

from app.summarization.chunker import chunk_text
from app.summarization.llm_client import LLMClient
from app.summarization.prompts import PromptLibrary


class SummarizationPipeline:
    def __init__(self, llm: LLMClient, prompts: PromptLibrary, logger: Any = None):
        self.llm = llm
        self.prompts = prompts
        self.log = logger

    def process(self, text: str, source_title: str = "",
                max_chunk_size: int = 3000, overlap: int = 300) -> dict:
        chunks = chunk_text(text, max_chunk_size, overlap)

        if not chunks:
            return {"summary": "", "insights": [], "action_items": [], "key_quotes": [],
                    "themes": [], "technical_concepts": [], "opportunities": [], "contradictions": []}

        chunk_summaries = []
        for chunk in chunks:
            result = self._summarize_chunk(chunk, source_title)
            chunk_summaries.append(result)

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        return self._synthesize(chunk_summaries, source_title)

    def process_structured(self, text: str, source_title: str = "",
                           max_chunk_size: int = 3000, overlap: int = 300) -> dict:
        base = self.process(text, source_title, max_chunk_size, overlap)
        insights = self._extract_insights(base["summary"], source_title)
        return {**base, **insights}

    def _summarize_chunk(self, chunk: dict, title: str) -> dict:
        prompt = self.prompts.render("summarize_chunk", text=chunk["text"], title=title)
        response = self.llm.chat([
            {"role": "system", "content": "You are an expert analyst. Return JSON with keys: summary, insights, action_items, key_quotes, themes, technical_concepts, opportunities, contradictions."},
            {"role": "user", "content": prompt},
        ])
        return self._parse_response(response)

    def _synthesize(self, chunk_summaries: list[dict], title: str) -> dict:
        summaries_text = "\n\n---\n\n".join(
            f"Chunk {i+1}:\n{s.get('summary', '')}" for i, s in enumerate(chunk_summaries)
        )
        prompt = self.prompts.render("synthesize", summaries=summaries_text, title=title)
        response = self.llm.chat([
            {"role": "system", "content": "You are an expert analyst synthesizing multiple summaries. Return JSON with keys: summary, insights, action_items, key_quotes, themes, technical_concepts, opportunities, contradictions."},
            {"role": "user", "content": prompt},
        ])
        return self._parse_response(response)

    def _extract_insights(self, summary: str, title: str) -> dict:
        prompt = self.prompts.render("extract_insights", summary=summary, title=title)
        response = self.llm.chat([
            {"role": "system", "content": "You extract deep insights, contradictions, and opportunities from content. Return JSON with keys: why_it_matters, suggested_next_actions, startup_opportunities, recurring_themes."},
            {"role": "user", "content": prompt},
        ])
        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            response = json_match.group(1).strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if self.log:
                self.log("Warning: LLM response was not valid JSON, treating as plain text")
            return {
                "summary": response,
                "insights": [],
                "action_items": [],
                "key_quotes": [],
                "themes": [],
                "technical_concepts": [],
                "opportunities": [],
                "contradictions": [],
            }
