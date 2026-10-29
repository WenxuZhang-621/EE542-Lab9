from collections import defaultdict
import json
from pathlib import Path
from rag.documents import extract_pages
from shared.contracts import Chunk

rows=[Chunk(**json.loads(line)) for line in Path('data/processed/chunks.jsonl').read_text().splitlines()]
assert len({row.chunk_id for row in rows})==len(rows)
assert all(0<len(row.text)<=500 for row in rows)
by_page=defaultdict(list)
for row in rows:
    assert row.source=='lab9-requirements.pdf'
    by_page[row.page].append(row)
original=extract_pages('lab9-requirements.pdf', Path('data/raw/part3-demo/lab9-requirements.pdf').read_bytes())
for page in original:
    covered=[False]*len(page.text)
    last_start=-1
    for chunk in by_page[page.page]:
        start=page.text.find(chunk.text, last_start+1)
        assert start>=0, (page.page, chunk.chunk_id)
        covered[start:start+len(chunk.text)]=[True]*len(chunk.text)
        last_start=start
    assert all(flag or char.isspace() for flag,char in zip(covered,page.text)), page.page
print(f'PASS: {len(rows)} unique Chunk-compatible rows, 6 source pages, <=500 chars, ordered source substrings, full non-whitespace coverage.')
