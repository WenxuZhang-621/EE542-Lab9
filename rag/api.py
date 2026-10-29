"""Owner C. Public interface used by A; no mock answers in production."""
from typing import List
from shared.contracts import Chunk, SearchHit
from shared.config import CONFIG

def build_index(chunks: List[Chunk]) -> None:
    raise NotImplementedError("C: implement OpenAI embedding and persistent index")

def retrieve(question: str, k: int = CONFIG["rag"]["retrieval_k"]) -> List[SearchHit]:
    raise NotImplementedError("C: implement query embedding and similarity retrieval")

def answer(question: str, session_id: str) -> str:
    raise NotImplementedError("C: implement context-only OpenAI conversation with memory")
