"""Show a real query embedding and stored vector.

Makes one OpenAI embedding request. Outputs only a short vector sample, never
credentials. Vector coordinates are learned features, not labeled word counts.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import faiss
import numpy as np
from rag.embeddings import embed_texts
from rag.vectorstore import load_store
from shared.config import ROOT, project_path


def trace(question, output):
    index, chunks, manifest = load_store(project_path('topic_index'))
    query, tokens = embed_texts([question], manifest['model'])
    raw_norm = float(np.linalg.norm(query[0]))
    faiss.normalize_L2(query)
    scores, positions = index.search(query, 4)
    hits = []
    for score, position in zip(scores[0], positions[0]):
        chunk = chunks[position]
        vector = index.reconstruct(int(position))
        hits.append({'rank': len(hits)+1, 'chunk_id': chunk.chunk_id,
            'source': chunk.source, 'page': chunk.page, 'text': chunk.text,
            'cosine_similarity': round(float(score), 6),
            'stored_vector_first_8': [round(float(x), 7) for x in vector[:8]],
            'stored_vector_l2_norm': round(float(np.linalg.norm(vector)), 7)})
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'question': question,
        'embedding_model': manifest['model'], 'dimensions': int(index.d),
        'indexed_chunks': int(index.ntotal), 'request_tokens': tokens,
        'raw_query_l2_norm': round(raw_norm, 7),
        'normalized_query_first_8': [round(float(x), 7) for x in query[0, :8]],
        'normalized_query_l2_norm': round(float(np.linalg.norm(query[0])), 7),
        'search': 'FAISS IndexFlatIP on unit-length vectors; inner product equals cosine similarity',
        'note': 'These eight coordinates are samples of a 1536-dimensional learned embedding. They are not B\'s normalized word-cluster histogram.',
        'top_4': hits}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', default='What is Form 8843 used for?')
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/a/embedding-trace.json')
    args = parser.parse_args()
    trace(args.question, args.output)
