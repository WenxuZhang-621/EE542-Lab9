"""Owner A. Wire this into ask_llm after C's retrieval API is ready.

This skeleton is deliberately not connected to the supplied plain-chat template.
"""
async def answer_with_sources(question: str, session_id: str) -> dict:
    raise NotImplementedError("A: retrieve context, call LLM, return answer and sources")
