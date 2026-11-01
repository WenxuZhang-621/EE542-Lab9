# Step 8: Part 4 topic data and knowledge base

2026-10-28 PDT, Wenxu's Mac. Topic: F-1 International Student Assistant (status, CPT/OPT, taxes).

| File | Content |
|---|---|
| build-kb.txt | `rag.cli --input data/raw/topic/corpus --index data/topic/index --build-only`: 17 documents stored, 1694 chunks (21–500 characters), text-embedding-3-small with 1536 dimensions, 163,063 tokens |
| cli-topic.txt | 6 real Q&A turns with `rag.cli --index data/topic/index` |

The source list, hashes, and cleanup rules are in data/topic/README.md and sources.lock.json.

Fixes made during processing:
- govinfo has no 2026 edition of Title 8, and the download returned a "Page Not Found" web page. A file-signature check was added, and the current 8 CFR 214.2 from eCFR as of 2026-09-30 is used instead, keeping only paragraph (f).
- Every page of the IRS PDFs has a printer's-proof header, and there were about 2000 end-of-line hyphenations and split words such as "Y ou" and "W -4". The PDFs were cleaned into page-separated text and the index was rebuilt (the indexes from the first two builds were deleted).

Results in cli-topic:
- The OPT unemployment limit is 90 days; the follow-up "And with the STEM extension?" is rewritten and answered with 150 days (over the whole OPT period).
- "How long can I stay in the U.S. after I finish my program?": the answer follows the regulation (30 days) and points out that another source says 60 days, which conflicts with the regulation.
- A question asked in Chinese is answered in Chinese. The transcript keeps the original text; the question asks how many hours per week an F-1 student may work on campus, and the answer is 20 hours per week while school is in session. An unrelated question (pizza) is answered as not covered by the documents.
- Gap: for "Do I need to file Form 8843 if I had no income?", the top 4 results miss the relevant passage, and the answer says the documents do not cover it.
