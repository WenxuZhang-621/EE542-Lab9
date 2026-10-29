"""Export selected MySQL document versions as traceable, bounded text chunks."""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from langchain_text_splitters import CharacterTextSplitter
from sqlalchemy import select
from rag.storage import documents, pages, get_engine
from shared.config import CONFIG, project_path
from shared.contracts import Chunk


def split_page(text: str, chunk_size: int, overlap: int, separator: str) -> list[str]:
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError('Require chunk_size > 0 and 0 <= overlap < chunk_size.')
    options = dict(chunk_size=chunk_size, chunk_overlap=overlap,
                   length_function=len, is_separator_regex=False,
                   keep_separator=True, strip_whitespace=False)
    splitter = CharacterTextSplitter(separator=separator, **options)
    # A long line has no newline boundary; the first splitter can exceed 500.
    fallback = CharacterTextSplitter(separator='', **options)
    result = []
    for part in splitter.split_text(text):
        pieces = fallback.split_text(part) if len(part) > chunk_size else [part]
        result.extend(piece for piece in pieces if piece.strip())
    return result


def build_chunks(engine, document_ids: list[str]) -> tuple[list[Chunk], dict]:
    settings = {k: CONFIG['rag'][k] for k in ('chunk_size', 'chunk_overlap', 'separator')}
    policy = {'settings': settings, 'splitter_version': version('langchain-text-splitters'),
              'policy': 'per-page-preserve-whitespace-long-line-character-fallback-v1'}
    chunks = []
    inputs = []
    with engine.connect() as conn:
        for document_id in sorted(set(document_ids)):
            doc = conn.execute(select(documents).where(
                documents.c.document_id == document_id)).mappings().one_or_none()
            if doc is None:
                raise ValueError(f'Unknown document ID: {document_id}')
            rows = conn.execute(select(pages).where(pages.c.document_id == document_id)
                                .order_by(pages.c.ordinal)).mappings().all()
            if len(rows) != doc['page_count']:
                raise ValueError('Stored page count mismatch; refusing incomplete export.')
            inputs.append({'document_id': document_id, 'source': doc['source'],
                           'sha256': doc['content_sha256'], 'pages': len(rows)})
            for row in rows:
                parts = split_page(row['text'], settings['chunk_size'],
                                   settings['chunk_overlap'], settings['separator'])
                for index, text in enumerate(parts):
                    identity = json.dumps([document_id, row['ordinal'], index, policy, text],
                                          ensure_ascii=False, sort_keys=True)
                    chunk_id = hashlib.sha256(identity.encode()).hexdigest()
                    chunks.append(Chunk(chunk_id, text, doc['source'], row['page_number']))
    if not chunks:
        raise ValueError('No non-empty chunks produced.')
    lengths = [len(chunk.text) for chunk in chunks]
    return chunks, {'inputs': inputs, **policy, 'chunk_count': len(chunks),
                    'min_chars': min(lengths), 'max_chars': max(lengths)}


def chunk_folder(folder: Path, write=print) -> list[Chunk]:
    """Store every supported file in the folder in MySQL, then chunk exactly those versions."""
    from rag.ingest import ingest_folder
    from rag.storage import init_schema
    engine = get_engine()
    try:
        init_schema(engine)
        results = ingest_folder(engine, folder)
        for result in results:
            detail = result.get('error') or f"{result['pages']} pages"
            write(f"Stored {result['source']}: {result['status']} ({detail})")
        ids = [result['document_id'] for result in results if result['status'] != 'failed']
        if not ids:
            raise ValueError('No file in the folder was stored.')
        chunks, manifest = build_chunks(engine, ids)
    finally:
        engine.dispose()
    write(f"Chunked {len(ids)} documents: {manifest['chunk_count']} chunks, "
          f"{manifest['min_chars']}-{manifest['max_chars']} characters")
    return chunks


def write_once_or_verify(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as output:
            output.write(content)
        return 'created'
    except FileExistsError:
        if path.read_text(encoding='utf-8') != content:
            raise ValueError(f'{path} already contains different data; choose a new --output path.')
        return 'unchanged'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document-id', action='append', required=True,
                        help='Exact document version; repeat to select multiple documents.')
    parser.add_argument('--output', type=Path, default=project_path('chunks'))
    args = parser.parse_args()
    engine = get_engine()
    try:
        chunks, manifest = build_chunks(engine, args.document_id)
    finally:
        engine.dispose()
    content = ''.join(json.dumps(asdict(chunk), ensure_ascii=False) + '\n' for chunk in chunks)
    manifest['output_sha256'] = hashlib.sha256(content.encode()).hexdigest()
    manifest_path = args.output.with_suffix('.manifest.json')
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    # Preflight both files before writing either, so existing evidence is preserved.
    for path, expected in [(args.output, content), (manifest_path, manifest_text)]:
        if path.exists() and path.read_text(encoding='utf-8') != expected:
            raise ValueError(f'{path} differs; choose a new --output path.')
    status = write_once_or_verify(args.output, content)
    write_once_or_verify(manifest_path, manifest_text)
    print(json.dumps({'status': status, 'output': str(args.output), **manifest}, ensure_ascii=False))


if __name__ == '__main__':
    main()
