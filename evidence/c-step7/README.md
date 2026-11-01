# Step 7: conversation chain with memory and the exit command line

2026-10-28 PDT, Wenxu's Mac. Embedding: text-embedding-3-small; chat: gpt-6-luna (default temperature, see c-step5); top-k=4.

| File | Content |
|---|---|
| offline-tests.txt | All 27 offline tests pass (the 3 MySQL tests are skipped by default), with DeprecationWarning treated as an error |
| cli-transcript.txt | 5 real Q&A turns with `python -m rag.cli`, with the questions given on stdin |
| cli-full-pipeline.txt | `python -m rag.cli --input data/raw/part3-lab-only`: PDF folder → MySQL → chunking → index → Q&A → exit |

What cli-transcript shows:

- The follow-up "How should that vector be normalized?" is rewritten into a complete question; the top result is the histogram passage on p.6 (0.679), and the answer is to divide by the chunk's total word count.
- The next follow-up, "What should we try after building it?", still resolves the reference correctly; the answer is to try different methods to improve it.
- For the unrelated question "What is the capital of France?", the retrieval scores are only 0.05–0.06 and the answer is "The documents do not cover…", with nothing made up.
- A question asked in Chinese is answered in Chinese. The transcript keeps the original text; the question asks which tool Part 3 uses to split the text and how large each chunk is, and the answer is LangChain's `CharacterTextSplitter` with a chunk size of 500.
- After `exit` the program quits (exit code 0), and the line after it is not asked.

cli-full-pipeline: the same PDF was already in the database, so it shows skipped (deduplicated by source and content hash). The 26 chunks were rebuilt in artifacts/indexes/openai-ef717012a5ba, with the same content as the default index.
Not done yet at this step: the upload page was not yet wired to ingest and indexing, the Part 4 topic data had not been started, and the website end to end and A's integration were not tested.
