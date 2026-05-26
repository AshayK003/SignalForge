import json
import re
from typing import Any

from app.summarization.chunker import chunk_text
from app.summarization.llm_client import LLMClient
from app.summarization.prompts import PromptLibrary


_PACE_X_SYSTEM: str | None = None


def _pace_x_prompt(prompts: PromptLibrary) -> str:
    global _PACE_X_SYSTEM
    if _PACE_X_SYSTEM is None:
        _PACE_X_SYSTEM = prompts.load("pace_x_system")
    return _PACE_X_SYSTEM


class SummarizationPipeline:
    def __init__(self, llm: LLMClient, prompts: PromptLibrary, logger: Any = None):
        self.llm = llm
        self.prompts = prompts
        self.log = logger.info if logger else None

    def process(self, text: str, source_title: str = "",
                max_chunk_size: int = 3000, overlap: int = 300) -> dict:
        chunks = chunk_text(text, max_chunk_size, overlap)

        if not chunks:
            return {"summary": "", "insights": [], "action_items": [], "key_quotes": [],
                    "themes": [], "technical_concepts": [], "opportunities": [],
                    "contradictions": [], "why_it_matters": "", "open_questions": []}

        chunk_summaries = []
        for chunk in chunks:
            result = self._summarize_chunk(chunk, source_title)
            chunk_summaries.append(result)

        if len(chunk_summaries) == 1:
            result = chunk_summaries[0]
        else:
            result = self._synthesize(chunk_summaries, source_title)

        return self._fill_defaults(result)

    def process_structured(self, text: str, source_title: str = "",
                           max_chunk_size: int = 3000, overlap: int = 300) -> dict:
        return self.process(text, source_title, max_chunk_size, overlap)

    def _summarize_chunk(self, chunk: dict, title: str) -> dict:
        prompt = self.prompts.render("summarize_chunk", text=chunk["text"], title=title)
        system = _pace_x_prompt(self.prompts)
        response = self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ])
        return self._parse_response(response)

    def _synthesize(self, chunk_summaries: list[dict], title: str) -> dict:
        summaries_text = "\n\n---\n\n".join(
            f"Chunk {i+1}:\n{s.get('summary', '')}" for i, s in enumerate(chunk_summaries)
        )
        prompt = self.prompts.render("synthesize", summaries=summaries_text, title=title)
        system = _pace_x_prompt(self.prompts)
        response = self.llm.chat([
            {"role": "system", "content": system},
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
                "summary": response[:5000],
                "core_ideas": [],
                "insights": [],
                "action_items": [],
                "key_quotes": [],
                "themes": [],
                "technical_concepts": [],
                "opportunities": [],
                "contradictions": [],
                "why_it_matters": "",
                "open_questions": [],
            }

    def _fill_defaults(self, result: dict) -> dict:
        defaults = {
            "summary": "",
            "core_ideas": [],
            "insights": [],
            "action_items": [],
            "key_quotes": [],
            "themes": [],
            "technical_concepts": [],
            "opportunities": [],
            "contradictions": [],
            "why_it_matters": "",
            "open_questions": [],
        }
        return {**defaults, **result}
