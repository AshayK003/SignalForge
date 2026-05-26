You are given multiple chunk summaries from the content "{title}". Synthesize them into a unified analysis.

Return a JSON object with these keys:
- "summary": A comprehensive 3-4 paragraph synthesis covering all major themes
- "insights": A list of 3-5 key insights that span across chunks
- "action_items": A list of 3-5 actionable takeaways
- "key_quotes": A list of 2-3 most important quotes
- "themes": A list of 2-5 recurring themes
- "technical_concepts": A list of 2-4 technical concepts
- "opportunities": A list of 2-3 opportunities, each as an object with "opportunity" and "why" fields
- "contradictions": A list of 2-3 contradictions or tensions

Chunk Summaries:
{summaries}
