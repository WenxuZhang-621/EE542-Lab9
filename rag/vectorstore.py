"""Build a local FAISS vector store with an ordered JSONL source mapping."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import faiss
import numpy as np
from rag.embeddings import embed_texts, embedding_model
from shared.config import project_path
from shared.contracts import Chunk


def chunks_json(chunks: list[Chunk]) -> str:
    if not chunks or any(not c.text.strip() for c in chunks):
        raise ValueError('Provide non-empty chunks.')
    if len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError('Duplicate chunk IDs.')
    return ''.join(json.dumps(asdict(c), ensure_ascii=False, sort_keys=True) + '\n' for c in chunks)


def make_index(vectors: np.ndarray):
    vectors = np.array(vectors, dtype='float32', order='C', copy=True)
    if vectors.ndim != 2 or min(vectors.shape) == 0 or not np.isfinite(vectors).all():
        raise ValueError('Expected a finite, non-empty 2D vector matrix.')
    if np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise ValueError('Zero vectors cannot be normalized.')
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def load_store(folder: Path):
    # Only load local artifacts produced by this application.
    manifest = json.loads((folder / 'manifest.json').read_text())
    for filename, field in [('chunks.jsonl','chunks_sha256'), ('index.faiss','index_sha256')]:
        if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != manifest[field]:
            raise ValueError(f'Corrupt index bundle: {filename}')
    chunks = [Chunk(**json.loads(line)) for line in (folder / 'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    index = faiss.read_index(str(folder / 'index.faiss'))
    if index.ntotal != len(chunks) or index.ntotal != manifest['count'] or index.d != manifest['dimension']:
        raise ValueError('Index/source mapping dimensions do not match.')
    return index, chunks, manifest


def build_store(chunks: list[Chunk], folder: Path, model: str) -> dict:
    content = chunks_json(chunks)
    digest = hashlib.sha256(content.encode()).hexdigest()
    if folder.exists():
        _, _, manifest = load_store(folder)
        if manifest['model'] != model or manifest['chunks_sha256'] != digest:
            raise ValueError('Existing index has different inputs/model; choose a new output folder.')
        return {'status': 'unchanged', **manifest}
    vectors, tokens = embed_texts([c.text for c in chunks], model)
    index = make_index(vectors)
    folder.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.index-building-', dir=folder.parent))
    try:
        faiss.write_index(index, str(staging / 'index.faiss'))
        (staging / 'chunks.jsonl').write_text(content, encoding='utf-8', newline='\n')
        manifest = {'provider': 'openai', 'model': model, 'dimension': index.d,
                    'count': index.ntotal, 'metric': 'cosine via normalized inner product',
                    'chunks_sha256': digest,
                    'index_sha256': hashlib.sha256((staging / 'index.faiss').read_bytes()).hexdigest(),
                    'total_tokens': tokens, 'created_at': datetime.now(timezone.utc).isoformat()}
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        load_store(staging)  # Verify persistence before exposing the finished bundle.
        if folder.exists():
            raise FileExistsError('Output appeared during build; refusing overwrite.')
        staging.rename(folder)
    finally:
        if staging.exists():
            shutil.rmtree(staging)  # Only our own unique temporary build directory.
    return {'status': 'created', **manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chunks', type=Path, default=project_path('chunks'))
    parser.add_argument('--output', type=Path, default=project_path('indexes') / 'openai')
    args = parser.parse_args()
    chunks = [Chunk(**json.loads(line)) for line in args.chunks.read_text().splitlines()]
    print(json.dumps(build_store(chunks, args.output, embedding_model()), ensure_ascii=False))


if __name__ == '__main__':
    main()
