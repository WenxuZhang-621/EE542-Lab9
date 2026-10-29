"""Part 4 evaluation set and OpenAI retrieval baseline, shared with B for Part 5.

  python -m rag.evaluate label      # questions.draft.jsonl -> questions.jsonl (relevant chunk IDs)
  python -m rag.evaluate baseline   # OpenAI retrieval on questions.jsonl -> baseline_openai.json

A chunk is relevant to a question when it contains any of the question's evidence phrases
(case and whitespace insensitive). Any embedding can be scored with score(questions, rankings).
"""
import argparse
from datetime import datetime, timezone
import json

from rag.retrieval import VectorStore
from rag.vectorstore import load_store
from shared.config import ROOT, project_path

DRAFT = ROOT / 'data/topic/questions.draft.jsonl'
BASELINE = ROOT / 'data/topic/baseline_openai.json'
KS = (1, 4, 10)


def normalize(text: str) -> str:
    text = text.replace('’', "'").replace('“', '"').replace('”', '"')
    return ' '.join(text.lower().split())


def read_jsonl(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def label(drafts: list[dict], chunks) -> list[dict]:
    texts = [(chunk.chunk_id, normalize(chunk.text)) for chunk in chunks]
    labelled = []
    for draft in drafts:
        phrases = [normalize(phrase) for phrase in draft['evidence']]
        ids = [chunk_id for chunk_id, text in texts if any(phrase in text for phrase in phrases)]
        if not ids:
            raise ValueError(f"No chunk contains the evidence for: {draft['question']}")
        labelled.append({'question': draft['question'], 'area': draft['area'],
                         'relevant_chunk_ids': ids, 'evidence': draft['evidence']})
    return labelled


def score(questions: list[dict], rankings: list[list[str]], ks=KS) -> dict:
    """rankings[i] is the ranked chunk ID list that an embedding returned for questions[i]."""
    rows = []
    for question, ranked in zip(questions, rankings, strict=True):
        relevant = set(question['relevant_chunk_ids'])
        first = next((rank for rank, chunk_id in enumerate(ranked, start=1) if chunk_id in relevant), None)
        rows.append({'question': question['question'], 'first_relevant_rank': first,
                     **{f'hit@{k}': first is not None and first <= k for k in ks},
                     **{f'recall@{k}': len(relevant & set(ranked[:k])) / len(relevant) for k in ks}})
    metrics = [f'hit@{k}' for k in ks] + [f'recall@{k}' for k in ks]
    summary = {metric: round(sum(row[metric] for row in rows) / len(rows), 4) for metric in metrics}
    summary['mrr'] = round(sum(1 / row['first_relevant_rank'] for row in rows
                               if row['first_relevant_rank']) / len(rows), 4)
    return {'questions': len(rows), 'summary': summary, 'per_question': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['label', 'baseline'])
    args = parser.parse_args()
    index_folder, questions_path = project_path('topic_index'), project_path('questions')
    if args.command == 'label':
        _, chunks, _ = load_store(index_folder)
        labelled = label(read_jsonl(DRAFT), chunks)
        questions_path.write_text(''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in labelled),
                                  encoding='utf-8')
        for q in labelled:
            print(f"{len(q['relevant_chunk_ids']):3d} relevant | {q['question']}")
        return
    questions = read_jsonl(questions_path)
    store = VectorStore(index_folder)
    hits = [store.search(q['question'], max(KS)) for q in questions]
    result = score(questions, [[hit.chunk.chunk_id for hit in row] for row in hits])
    for row, found in zip(result['per_question'], hits):
        row['top'] = [[hit.chunk.chunk_id, round(hit.score, 4)] for hit in found]
    result = {'method': 'OpenAI embedding, cosine similarity', 'model': store.manifest['model'],
              'index_chunks_sha256': store.manifest['chunks_sha256'],
              'created_at': datetime.now(timezone.utc).isoformat(), **result}
    BASELINE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
