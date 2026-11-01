# A: Real QA evaluation and known issues

On 2026-10-31, one run used C's fixed 32 questions, OpenAI `text-embedding-3-small`, local Llama 3.1 8B Q4_K_M, and A's actual QA service. Each question used a separate session; the run did not insert 32 test messages into shared chat. `evidence/a/evaluation.json` records the question-set SHA-256, answers, full sources, and timings.

| Metric | Result | Interpretation |
|---|---|---|
| Service returned an answer | 32/32 | No service exception; not a correctness score |
| At least one valid citation number | 32/32 | The number exists among returned sources; does not verify support for the claim |
| Selected passages hit at least one annotated chunk | 30/32 | Based on C's fixed annotations, which may not cover every valid source |
| Expanded context hit an annotated chunk | 30/32 | Coverage after adding adjacent passages |
| Cited context hit an annotated chunk | 28/32 | Citation coverage, not factual accuracy |
| Median time per question | 0.963 seconds | This run on this computer; not representative of other hardware/networks |

## Human review findings

These comparisons concern the repository's fixed source snapshots, not current law. Do not use these sample answers directly for real immigration or tax decisions.

| Question | Observed issue | Follow-up |
|---|---|---|
| 3 | Asked about entry timing but answered with visa-issuance timing; the source has different numbers for different actions | Preserve as a regression case for selecting the requested fact |
| 4 | Gave a number, but the cited passage did not cover C's annotated core evidence | Check whether each citation actually supports its associated claim |
| 5 | The eCFR snapshot and another government page give different deadlines; the answer chose one without disclosing the conflict | C should check source versions and applicability; A's prompt is not a reliable conflict detector |
| 12 | Did not retrieve the annotated on-campus employment passage; acknowledged insufficient evidence | C should review retrieval coverage; abstention is preferable to an unsupported claim |
| 16 | Sources differ on the OPT application deadline; the answer did not explain the difference | Review dates, versions, and consistency with C |
| 23 | Rephrased a time relationship into an unsupported start/end range | Preserve as a factual-generation regression case |
| 27 | Missed the annotated Form 8843 evidence and failed to name the form | C should review retrieval coverage |

Question 11 also included unrequested off-campus employment information, showing room to improve concision and category separation. The remaining answers have not been formally certified as entirely correct.

Two experimental prompt adjustments did not reliably fix these issues and did not replace the verified production prompt. C's original sources, questions, annotations, and baseline were not changed to inflate scores. This is local functional testing and limited case validation, **not a mature product for legal advice**.

## Reproduction

From the repository root, with local services and your own authorized key configured:

```sh
python -m scripts.evaluate_a
python -m scripts.trace_embedding
```

The first command calls real embeddings and local Llama. The second makes one additional embedding request and saves the first eight query-vector coordinates, 1,536-dimensional metadata, L2 norms, four top hits, and cosine similarities. Outputs contain no keys.
