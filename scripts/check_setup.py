"""Read-only A preflight; --live asks one question using the configured services."""
import argparse
import asyncio
import hashlib
import json
import os
import httpx
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from shared.config import ROOT, CONFIG

async def check(live=False):
    load_dotenv(ROOT/'.env')
    checks = {}
    folder = ROOT/'data/topic/index'
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    checks['index_integrity'] = all(hashlib.sha256((folder/name).read_bytes()).hexdigest() == manifest[key]
        for name, key in [('chunks.jsonl','chunks_sha256'), ('index.faiss','index_sha256')])
    checks['jwt_secret'] = len(os.getenv('JWT_SECRET', '')) >= 32 and not os.getenv('JWT_SECRET', '').startswith('please_change')
    checks['openai_key_configured'] = bool(os.getenv('OPENAI_API_KEY', '').strip())
    engine = None
    try:
        engine = create_async_engine(os.environ['DATABASE_URL'])
        async with engine.connect() as connection:
            await connection.execute(text('SELECT 1'))
        checks['mysql_connection'] = engine.dialect.name == 'mysql'
        checks['database_connection'] = True
    except Exception:
        checks['database_connection'] = checks['mysql_connection'] = False
    finally:
        if engine is not None: await engine.dispose()
    base = os.getenv('LLM_API_BASE', CONFIG['services']['llm_api_base']).rstrip('/')
    try:
        key = os.getenv('LLM_API_KEY', '')
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(base+'/models', headers={'Authorization':f'Bearer {key}'} if key else {})
            response.raise_for_status()
            checks['llama_reachable'] = bool(response.json().get('data'))
    except Exception:
        checks['llama_reachable'] = False
    if live and all(checks.values()):
        from webapp.backend.rag_service import answer_with_sources, ServiceError
        try:
            result = await answer_with_sources('What is Form 8843 used for?', 'preflight')
            checks['live_rag_answer'] = bool(result['answer'] and result['sources'])
            checks['live_answer_has_citations'] = not result.get('citation_warning', True)
            # Source IDs and generated response are useful evidence; no credentials included.
            print(json.dumps({'live_result': result}, ensure_ascii=False, indent=2))
        except ServiceError as exc:
            checks['live_rag_answer'] = False
            checks['live_error_code'] = exc.code
    print(json.dumps(checks, indent=2))
    return all(value is True for value in checks.values())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(check(args.live)) else 1)
