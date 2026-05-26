You are generating a weekly intelligence report for {week_start} to {week_end}.

{source_count} sources were processed this week. Here are their summaries:

{sources}

Produce a structured report as JSON with these keys:
- "executive_summary": a high-density narrative synthesis of the most important developments this week
- "key_developments": list of the most significant developments, ordered by importance
- "cross_source_connections": list of notable connections or contradictions between sources
- "recommended_actions": list of concrete decisions or actions that should follow
- "signals_to_monitor": list of patterns, trends, or signals worth watching

Make the synthesis insightful and cross-referenced. Do not just list summaries.
