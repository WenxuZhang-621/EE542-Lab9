"""Part 3-III driver: build or reuse the index, then answer questions until 'exit'.

  python -m rag.cli                   # index from data/processed/chunks.jsonl
  python -m rag.cli --input FOLDER    # PDF folder -> MySQL -> chunks -> index -> questions
"""
import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from rag.chain import OpenAIChat, chat_model, create_conversation_chain
from rag.embeddings import embedding_model
from rag.retrieval import VectorStore
from rag.vectorstore import build_store, chunks_json
from shared.config import CONFIG, project_path
from shared.contracts import Chunk


def chunks_from_folder(folder: Path) -> list[Chunk]:
    from rag.chunking import build_chunks
    from rag.ingest import ingest_folder
    from rag.storage import get_engine, init_schema
    engine = get_engine()
    try:
        init_schema(engine)
        results = ingest_folder(engine, folder)
        for result in results:
            detail = result.get('error') or f"{result['pages']} pages"
            print(f"Stored {result['source']}: {result['status']} ({detail})")
        ids = [result['document_id'] for result in results if result['status'] != 'failed']
        if not ids:
            raise ValueError('No PDF in the folder was stored.')
        chunks, manifest = build_chunks(engine, ids)
    finally:
        engine.dispose()
    print(f"Chunked: {manifest['chunk_count']} chunks, {manifest['min_chars']}-{manifest['max_chars']} characters")
    return chunks


def preview(text: str, limit: int = 160) -> str:
    line = ' '.join(text.split())
    return line if len(line) <= limit else line[:limit - 1] + '…'


def repl(chain, session_id: str, *, read=input, write=print, echo: bool = False) -> None:
    write("Type a question, or 'exit' to quit.")
    while True:
        try:
            question = read('\nQuestion: ').strip()
        except (EOFError, KeyboardInterrupt):
            write('')
            return
        if echo:
            write(question)  # Piped input is not shown by the terminal; keep transcripts readable.
        if question.lower() == 'exit':
            return
        if not question:
            continue
        try:
            result = chain.ask(question, session_id)
        except Exception as exc:
            # Keep the loop alive; the chain does not store a failed turn in memory.
            write(f'Error ({type(exc).__name__}): {exc}')
            continue
        if result.standalone_question != question:
            write(f'Standalone question: {result.standalone_question}')
        write(f'\nAnswer: {result.answer}\n\nRetrieved context:')
        for number, hit in enumerate(result.hits, start=1):
            page = f' p.{hit.chunk.page}' if hit.chunk.page is not None else ''
            write(f'  [{number}] score {hit.score:.3f} · {hit.chunk.source}{page} · {hit.chunk.chunk_id[:12]}')
            write(f'      {preview(hit.chunk.text)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, help='PDF folder to extract, store and chunk first.')
    parser.add_argument('--chunks', type=Path, default=project_path('chunks'))
    parser.add_argument('--index', type=Path, help='Index folder; the default depends on the input.')
    parser.add_argument('-k', type=int, default=CONFIG['rag']['retrieval_k'])
    args = parser.parse_args()
    try:
        if args.input:
            chunks = chunks_from_folder(args.input)
        else:
            chunks = [Chunk(**json.loads(line))
                      for line in args.chunks.read_text(encoding='utf-8').splitlines()]
        folder = args.index
        if folder is None and args.input:
            # One folder per chunk set, because build_store never overwrites a different index.
            digest = hashlib.sha256(chunks_json(chunks).encode()).hexdigest()
            folder = project_path('indexes') / f'openai-{digest[:12]}'
        folder = folder or project_path('indexes') / 'openai'
        built = build_store(chunks, folder, embedding_model())
        chain = create_conversation_chain(OpenAIChat(chat_model()), VectorStore(folder), args.k)
    except SQLAlchemyError:
        # Do not print connection strings or SQL parameters.
        print('Setup failed: database operation failed. Check MySQL and DATABASE_URL.', file=sys.stderr)
        return 1
    except Exception as exc:
        print(f'Setup failed ({type(exc).__name__}): {exc}', file=sys.stderr)
        return 1
    print(f"Index {built['status']}: {built['count']} chunks, {built['model']} ({built['dimension']} dims)")
    print(f'Chat model: {chain.llm.model}, top-k: {chain.k}')
    repl(chain, f'cli-{uuid.uuid4().hex[:8]}', echo=not sys.stdin.isatty())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
