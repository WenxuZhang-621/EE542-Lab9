# Step 10: upload page integration and tests

2026-10-28 PDT.

| File | Content |
|---|---|
| process-uploads.txt | Real run of `process_uploads()`: 2 web pages and the lab PDF stored in MySQL (skipped if already present), and a .docx shown as a failed row. After 38 chunks were indexed, a question about the ITIN was answered with Form W-7, with all sources from sits-itin.html |
| browser-processed.jpg, browser-answer.jpg | Browser at 127.0.0.1:8501: a Markdown test file was submitted through the page's file input (a script put the file into the input, which is equivalent to choosing it). After Process documents was clicked, the page showed the stored document, 1 chunk, and a 1536-dimension index; a question then got the correct answer with sources |
| tests.txt | `LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v`: all 39 tests pass (including 3 MySQL tests and 3 Streamlit AppTests) |

The browser test left a test document, browser-upload-test.md, in MySQL and artifacts/indexes/upload-* indexes on disk; neither is in Git.
