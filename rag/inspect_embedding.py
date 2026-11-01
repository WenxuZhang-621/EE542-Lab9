"""Part 3-II.3 / III.2 demo: the vectors behind one retrieval.

  python -m rag.inspect_embedding "How many days of unemployment are allowed on post-completion OPT?"
  python -m rag.inspect_embedding "QUESTION" --index data/topic/index -k 4

Embeds the question with the index's own model, then prints each top-k chunk with the vector
stored for it and the score recomputed as a dot product, next to the score FAISS returned.
"""
import argparse
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from rag.cli import preview
from rag.embeddings import embed_texts
from rag.vectorstore import load_store
from shared.config import CONFIG, project_path
from shared.contracts import Chunk


@dataclass(frozen=True)
class Match:
    chunk: Chunk
    vector: np.ndarray
    faiss_score: float
    dot_product: float


def explain(question: str, folder: Path, k: int, *, client=None) -> tuple[np.ndarray, list[Match], dict]:
    if not question.strip():
        raise ValueError('Question must not be empty.')
    index, chunks, manifest = load_store(Path(folder))
    query, _ = embed_texts([question], manifest['model'], client=client)
    faiss.normalize_L2(query)
    scores, rows = index.search(query, min(k, index.ntotal))
    matches = []
    for score, row in zip(scores[0], rows[0]):
        vector = index.reconstruct(int(row))  # Stored at build time, already normalized to length 1.
        matches.append(Match(chunks[row], vector, float(score), float(vector @ query[0])))
    return query[0], matches, manifest


def head(vector: np.ndarray, n: int = 6) -> str:
    return '[' + ', '.join(f'{x:+.4f}' for x in vector[:n]) + ', …]'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('question')
    parser.add_argument('--index', type=Path, default=project_path('topic_index'))
    parser.add_argument('-k', type=int, default=CONFIG['rag']['retrieval_k'])
    args = parser.parse_args()
    query, matches, manifest = explain(args.question, args.index, args.k)
    print(f"Index: {manifest['count']} chunks, {manifest['model']}, {manifest['dimension']} dimensions")
    print(f'\nQuestion: {args.question}')
    print(f'Question vector ({len(query)} numbers): {head(query)}  length {np.linalg.norm(query):.3f}')
    for rank, match in enumerate(matches, start=1):
        chunk = match.chunk
        page = f' p.{chunk.page}' if chunk.page is not None else ''
        print(f'\n[{rank}] {chunk.source}{page} · {chunk.chunk_id[:12]} · {len(chunk.text)} characters')
        print(f'    text:   {preview(chunk.text, 150)}')
        print(f'    vector: {head(match.vector)}  length {np.linalg.norm(match.vector):.3f}')
        print(f'    score:  dot product {match.dot_product:.3f} (FAISS {match.faiss_score:.3f})')


if __name__ == '__main__':
    main()
