"""Search a saved index: embed the question with the index's own model, return top-k chunks."""
from pathlib import Path

import faiss
from rag.embeddings import embed_texts
from rag.vectorstore import load_store
from shared.contracts import SearchHit


class VectorStore:
    def __init__(self, folder: Path, *, client=None):
        self.folder = Path(folder)
        self.index, self.chunks, self.manifest = load_store(self.folder)
        self.client = client

    def search(self, question: str, k: int) -> list[SearchHit]:
        if not question.strip():
            raise ValueError('Question must not be empty.')
        if k <= 0:
            raise ValueError('k must be positive.')
        # Query and chunks must share one model, so use the one recorded at build time.
        query, _ = embed_texts([question], self.manifest['model'], client=self.client)
        if query.shape[1] != self.index.d:
            raise ValueError('Query embedding dimension does not match the index.')
        faiss.normalize_L2(query)
        scores, rows = self.index.search(query, min(k, self.index.ntotal))
        return [SearchHit(self.chunks[row], float(score))
                for score, row in zip(scores[0], rows[0]) if row >= 0]
