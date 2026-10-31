"""Run A against C's frozen question set using real embeddings and local Llama.

This spends a small amount of embedding API usage. Report retrieval/citation
coverage separately from factual correctness; the latter needs human review.
Does not create website accounts or add messages to the shared room.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time

from shared.config import ROOT, project_path
from webapp.backend.rag_service import RAGService, ServiceError


async def evaluate(output, limit=None):
    question_file = project_path('questions')
    questions = [json.loads(line) for line in question_file.read_text(encoding='utf-8').splitlines() if line.strip()]
    if limit is not None:
        questions = questions[:limit]
    service = RAGService()
    rows = []
    started = datetime.now(timezone.utc).isoformat()
    for number, item in enumerate(questions, 1):
        tick = time.perf_counter()
        row = {'id': number, 'question': item['question'], 'area': item['area'],
               'reference_chunk_ids': item['relevant_chunk_ids'], 'reference_evidence': item['evidence']}
        try:
            result = await service.answer(item['question'], f'eval:{started}:{number}')
            sources = result['sources']
            selected = {source['chunk_id'] for source in sources}
            expanded = {chunk_id for source in sources for chunk_id in source['context_chunk_ids']}
            cited = {chunk_id for source in sources if source.get('cited') for chunk_id in source['context_chunk_ids']}
            gold = set(item['relevant_chunk_ids'])
            row.update(success=True, answer=result['answer'], sources=sources,
                valid_citation_present=not result.get('citation_warning', True),
                selected_gold_hit=bool(selected & gold), context_gold_hit=bool(expanded & gold),
                cited_context_gold_hit=bool(cited & gold))
        except ServiceError as error:
            row.update(success=False, error_code=error.code)
        row['latency_seconds'] = round(time.perf_counter()-tick, 3)
        rows.append(row)
        if number % 4 == 0 or number == len(questions):
            print(f'Evaluated {number}/{len(questions)} questions', flush=True)
    summary = {'questions': len(rows), 'successful_answers': sum(row['success'] for row in rows),
        **{field: sum(row.get(field, False) for row in rows) for field in
           ('valid_citation_present', 'selected_gold_hit', 'context_gold_hit', 'cited_context_gold_hit')},
        'median_latency_seconds': round(statistics.median(row['latency_seconds'] for row in rows), 3)}
    report = {'started_at': started, 'model': service.model, 'question_set': str(question_file.relative_to(ROOT)),
        'question_set_sha256': hashlib.sha256(question_file.read_bytes()).hexdigest(),
        'limitations': 'One run on the frozen corpus. Gold labels may be incomplete. Retrieval overlap and valid citation numbers do not establish answer correctness or current legal accuracy. Human review is required.',
        'summary': summary, 'results': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary['successful_answers'] == len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/a/evaluation.json')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    raise SystemExit(0 if asyncio.run(evaluate(args.output, args.limit)) else 1)
