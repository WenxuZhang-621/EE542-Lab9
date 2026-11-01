# Part 3-II.1 evidence: storing the original text in MySQL

Recorded: 2026-10-28T17:33:41.468285-07:00
Base: 6ba2ae8 plus uncommitted source changes. Setup: a separate Docker MySQL 8.4 at 127.0.0.1:13306, database groupchat.
Input hashes, sources, and page counts are in import-first.jsonl. The original files were kept; data/raw/part3-demo holds copies.

Commands and exit codes:
- python -m rag.ingest --input data/raw/part3-demo: 0 for both the first and the repeated run; see import-first.jsonl / import-repeat.jsonl.
- LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v: 0, 7 tests passed; see tests.txt.
- PYTHONPATH=. python evidence/c-step2/verify_readback.py: 0, the original text of every page matches; see readback.txt.

pdf-warnings.log keeps the parser warnings for special fonts; the glyph accuracy of the full Ads cookbook text has not been confirmed. MySQL was not replaced by a mock database, and no embedding or LLM calls were made.
At the time of this record the database was left running, with its data kept in a Docker named volume; it was bound only to a local port and not deployed publicly.
