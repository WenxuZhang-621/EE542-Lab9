"""Owner C. Public interface used by A; no mock answers in production."""
from functools import lru_cache
from typing import List
from shared.contracts import Chunk, SearchHit
from shared.config import CONFIG, project_path

INDEX = project_path("indexes") / "openai"

def build_index(chunks: List[Chunk]) -> None:
    from rag.embeddings import embedding_model
    from rag.vectorstore import build_store
    build_store(chunks, INDEX, embedding_model())

@lru_cache(maxsize=1)
def _vectorstore():
    from rag.retrieval import VectorStore
    # Loaded once per process; restart the caller after rebuilding the index.
    return VectorStore(INDEX)

@lru_cache(maxsize=1)
def _chain():
    from rag.chain import OpenAIChat, chat_model, create_conversation_chain
    return create_conversation_chain(OpenAIChat(chat_model()), _vectorstore())

def retrieve(question: str, k: int = CONFIG["rag"]["retrieval_k"]) -> List[SearchHit]:
    """Synchronous OpenAI call; async callers should run it in a worker thread."""
    return _vectorstore().search(question, k)

def answer(question: str, session_id: str) -> str:
    return _chain().ask(question, session_id).answer
