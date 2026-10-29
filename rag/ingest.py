"""python -m rag.ingest --input data/raw [--recursive]. PDF, TXT, Markdown and HTML; JSONL output, no secrets."""
import argparse
import json
import sys
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from rag.documents import MAX_BYTES, SUPPORTED_SUFFIXES, extract_pages
from rag.storage import get_engine, init_schema, save_document
from shared.config import project_path


def ingest_bytes(engine, source: str, content: bytes) -> dict:
    """Extract and store one file; failures become a result row instead of stopping the batch."""
    try:
        if len(content) > MAX_BYTES:
            raise ValueError('File exceeds the 20 MiB extraction limit.')
        return save_document(engine, source, content, extract_pages(source, content))
    except SQLAlchemyError:
        # Do not log connection strings, SQL parameters, or document text.
        return {'source': source, 'status': 'failed', 'error': 'Database operation failed.'}
    except (ValueError, OSError) as exc:
        return {'source': source, 'status': 'failed', 'error': str(exc)}
    except Exception as exc:
        return {'source': source, 'status': 'failed', 'error': type(exc).__name__}


def ingest_folder(engine, folder: Path, recursive: bool = False) -> list[dict]:
    if not folder.is_dir():
        raise ValueError(f'Input folder does not exist: {folder}')
    paths = sorted(p for p in (folder.rglob('*') if recursive else folder.iterdir())
                   if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
    if not paths:
        raise ValueError('No PDF, TXT, Markdown or HTML files found in input folder.')
    results = []
    for path in paths:
        source = path.relative_to(folder).as_posix()
        if path.stat().st_size > MAX_BYTES:
            results.append({'source': source, 'status': 'failed',
                            'error': 'File exceeds the 20 MiB extraction limit.'})
            continue
        results.append(ingest_bytes(engine, source, path.read_bytes()))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=project_path('raw'))
    parser.add_argument('--recursive', action='store_true')
    args = parser.parse_args()
    engine = None
    try:
        engine = get_engine()
        init_schema(engine)
        results = ingest_folder(engine, args.input, args.recursive)
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': type(exc).__name__,
                          'hint': 'Check the input folder and MySQL/.env configuration.'}), file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    return int(any(r['status'] == 'failed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
