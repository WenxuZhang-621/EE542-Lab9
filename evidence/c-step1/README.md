# C step 1 verification record

Time: 2026-10-28T17:23:58.033147-07:00
Base commit: 6ba2ae8, with uncommitted changes.
Python: 3.12.13; dependencies: rag/requirements.txt.
Input: lab9-f26.pdf, SHA-256 867bc2f8eebf2d35f4884c644c0f9755a070f591512677c53521958e981aff4c.

Run: `python -m unittest discover -s tests -v` (exit code 0), plus a PdfReader check on the real document and a Streamlit AppTest (exit code 0); results are in checks.txt.
AppTest injects a file object, so it verifies page processing and rendering, not an end-to-end browser upload.
The page was started at 127.0.0.1:8501.
Not verified at this step: the database, embeddings, retrieval, model answers, and the final topic data.
