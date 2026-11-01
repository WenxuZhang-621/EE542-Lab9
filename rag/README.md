# C: Data and RAG

C owns Part 3 (document upload, database ingest, chunking, the OpenAI vector store, Q&A with memory, and the command line) and the Part 4 topic knowledge base.

Run from the repository root. First run `cp -n .env.example .env` and fill in `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, and `OPENAI_CHAT_MODEL` (currently gpt-6-luna, which accepts only the default temperature, so the code does not pass that parameter). Dependencies (Python 3.12+): `python -m pip install -r rag/requirements.txt`. Local MySQL: `docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait` (port 13306).

## Modules

| File | Purpose | PDF section |
|---|---|---|
| `documents.py` | Extracts text from PDF, TXT, Markdown, and HTML; keeps only the main content of HTML; splits text with form feeds into pages | Part 3-I |
| `ingest.py` | Stores a folder or a single file in MySQL (a document version plus the original text of each page); skips duplicate content | II.1 |
| `chunking.py` | `CharacterTextSplitter` with 500 characters, 100 overlap, and newlines as the separator; `chunk_folder()` chunks the files after ingest | II.2 |
| `embeddings.py`, `vectorstore.py` | OpenAI embeddings (official endpoint) and a FAISS cosine index, saved together with chunks.jsonl and a manifest | II.3 |
| `retrieval.py` | Embeds the question with the model recorded in the index and returns the top k | III.2 |
| `inspect_embedding.py` | Shows the vectors of the question and the top-k chunks (first few dimensions and length) and recomputes the retrieval scores as dot products | II.3, III.2 |
| `chain.py` | Keeps one conversation buffer per session; rewrites follow-up questions before retrieval; answers only from the retrieved passages, cites them, and points out conflicts | II.4, III.3 |
| `cli.py` | Driver: can run the full pipeline from a folder, then asks questions in a loop until `exit` | III.1 |
| `upload_app.py` | Upload page: upload one or more files in the sidebar → ingest → chunk → build the index → ask questions | Part 3-I |
| `topic_data.py`, `evaluate.py` | Part 4 source download and cleanup; the evaluation question set and the OpenAI retrieval baseline | Part 4 |
| `api.py` | Interface for A: `retrieve()` and `answer()`, reading `data/topic/index` | Part 4 |

## Common commands

```sh
python -m rag.run_upload                       # upload page at http://127.0.0.1:8501
python -m rag.cli --index data/topic/index     # command-line Q&A over the topic knowledge base
python -m rag.inspect_embedding "question"     # show the question and result vectors and recompute the scores
python -m rag.cli                              # Part 3 sample: reads data/processed/chunks.jsonl on C's machine (not in Git; use --index after cloning)
python -m rag.cli --input folder               # any folder: ingest → chunk → build index → Q&A
python -m unittest discover -s tests           # offline tests; set LAB9_TEST_MYSQL=1 to include the database tests
```

Topic sources, knowledge-base files, and the evaluation method are described in [data/topic/README.md](../data/topic/README.md). Run records are in `evidence/c-step1` through `c-step10`.
