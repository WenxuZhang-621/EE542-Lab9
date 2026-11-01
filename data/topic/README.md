# Part 4 knowledge base: F-1 International Student Assistant

Topic: maintaining F-1 status, on- and off-campus work (CPT/OPT/STEM OPT), and U.S. taxes for F-1 students. All sources are official U.S. federal government publications. Answers are general information only and are not legal or tax advice.

| File | Content | Used by |
|---|---|---|
| `sources.json` | Title, publisher, URL, and cleanup method of the 17 sources | Whole team |
| `sources.lock.json` | Byte count, SHA-256, and download time of each downloaded file | Reproduction |
| `catalog.json` | Maps a chunk's `source` (corpus file name) to its title, publisher, and URL | A, to show source links |
| `index/` | FAISS index, `chunks.jsonl` in the same order, and `manifest.json` (1694 chunks, text-embedding-3-small, 1536 dimensions) | A: `rag.api.retrieve()`; B: reads `chunks.jsonl` |
| `questions.draft.jsonl` | 32 evaluation questions, each with evidence sentences quoted from the sources | Edit this file to change the questions |
| `questions.jsonl` | Relevant chunk IDs, labeled from the evidence sentences | B's evaluation input |
| `baseline_openai.json` | OpenAI embedding retrieval baseline: hit@k, recall@k, MRR, and the rank for each question | B, for comparison |

## Reproduction

```sh
python -m rag.topic_data fetch      # download to data/raw/topic/downloads (not committed)
python -m rag.topic_data curate     # clean into data/raw/topic/corpus
python -m rag.cli --input data/raw/topic/corpus --index data/topic/index --build-only
python -m rag.evaluate label        # relabel questions.jsonl
python -m rag.evaluate baseline     # recompute the OpenAI baseline
```

Cleanup rules: from 8 CFR 214.2 only the (f) F-1 section is kept, using the current eCFR text as of 2026-09-30 (govinfo has no 2026 edition yet). In the two IRS PDFs, the printer's-proof header is removed from every page, words broken by end-of-line hyphens or letter spacing are rejoined, and the text is saved with page separators so page numbers are kept. Only the main content of each web page is kept. Delete `index/` before rebuilding the index, because an existing index is never overwritten.

## Known conflict

The 2026 revision of 8 CFR 214.2(f) switches to a fixed period of admission (at most 4 years), 30 days to depart after it ends, and an OPT application deadline of 30 days after the program ends. Some older Study in the States and USCIS pages still say 60 days. The Q&A prompt tells the model to point out the conflict and prefer the regulation or the newer source. The evaluation questions are labeled by the regulation; for the question on the OPT application deadline, both statements are labeled relevant.

## How B compares

Rank the chunk IDs for each question with your own embedding, then:

```python
from rag.evaluate import read_jsonl, score
from shared.config import project_path
questions = read_jsonl(project_path('questions'))
result = score(questions, rankings)   # rankings[i]: ordered chunk_id list for question i
```

Results can be compared directly with `baseline_openai.json` only when they use the same `index/chunks.jsonl` and the same metrics.
