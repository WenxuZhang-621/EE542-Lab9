# Step 6: real OpenAI vector store and retrieve()

2026-10-28 PDT, Wenxu's Mac. Input: data/processed/chunks.jsonl (the lab handout PDF, 6 pages → 26 chunks, output_sha256 3eb28f90…).

| File | Content |
|---|---|
| build-index.txt | First build with `python -m rag.vectorstore`: created, text-embedding-3-small, 1536 dimensions, 26 vectors, 2835 tokens |
| rebuild-reuse.txt | Second run: unchanged, no new API calls |
| reload-check.txt | Reload with load_store: 26 vectors / 1536 dimensions / 26 chunks, hash check passed |
| retrieve-samples.txt | Real `rag.api.retrieve()` queries for 3 questions: top-4 scores (cosine), pages, and chunk IDs |
| retrieve_samples.py | Script that produced the record above |

For all 3 questions the top result is the matching passage: chunk size → the CharacterTextSplitter passage on p.4 (0.478); histogram normalization → the Part 5 passage on p.6 (0.626); video requirements → the Deliverables passage on p.6 (0.501).
The index is in artifacts/indexes/openai (ignored by Git). This is only a sample run of the Part 3 pipeline, not the Part 4 topic knowledge base.
