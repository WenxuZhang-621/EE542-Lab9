"""Owner A. Wire this into ask_llm.

C's rag.api.retrieve(question, k) is ready and reads data/topic/index; it is a blocking
OpenAI call, so run it in a worker thread. See docs/interfaces.md for sources and the notice.
This skeleton is not yet connected to the supplied plain-chat template.
"""
async def answer_with_sources(question: str, session_id: str) -> dict:
    raise NotImplementedError("A: retrieve context, call LLM, return answer and sources")
