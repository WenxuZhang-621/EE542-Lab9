# B: Custom embedding (Part 5)

Following the PDF's Part 5 method, the 1694 text chunks of the Part 4 knowledge base are vectorized again: **Word2Vec word vectors → our own k-means into K clusters with centroids → a normalized K-dimensional word histogram for each chunk**. Improvements are then tried on the same evaluation and compared with C's OpenAI retrieval baseline.

## Files

| File | Content |
|---|---|
| `tokenize.py` | Shared tokenizer (lowercase; keeps numbers and hyphenated words such as `f-1` and `1040-nr`), with an optional stop-word list. Training, documents, and queries must use the same tokenizer |
| `kmeans.py` | **Our own k-means**: k-means++ initialization, Lloyd iterations, and empty-cluster handling; Euclidean or spherical (cosine) distance; NumPy only. Also provides hard and soft assignment |
| `model.py` | `HistogramEmbedder`: training (gensim Word2Vec → k-means → IDF), `embed()`, and save/load; every improvement is a switch on `HistogramConfig` |
| `api.py` | Team interface `fit(chunks, n, k)` / `embed(text)`. The model is stored in `artifacts/custom_embedding/<name>` (not committed), and documents and queries share one fitted model |
| `evaluate.py` | Experiment grid: baseline, parameter sweeps, single improvements, combinations, and seed sensitivity; writes to `evidence/b-part5/` |
| `../tests/test_custom_embedding.py` | 12 checks: distances match NumPy, k-means separates three clusters with non-increasing inertia, the histogram sums to "known words / total words", and a saved model reloads with identical results |

## Run

```sh
python -m unittest tests.test_custom_embedding -v
python -m custom_embedding.evaluate            # all experiments, about 3 minutes -> evidence/b-part5/results.{json,md}, metrics.png
python -m custom_embedding.api fit --best      # fit and save the model with the best configuration
python -m custom_embedding.api embed "How many months of OPT can a student get at each degree level?"
```

Dependencies: `rag/requirements.txt` plus `gensim`, `scikit-learn` (used only for an optional comparison), and `matplotlib` (plots). Python 3.12+.

## Method

**Baseline (as written in the PDF)**, `HistogramConfig()`:
1. Train Word2Vec on the tokens of the 1694 chunks (skip-gram, N=100, window 5, min_count=2, 30 epochs, fixed seed), which gives vectors for 3039 words.
2. Our own k-means groups these 3039 word vectors into K=200 clusters with 200 centroids.
3. A chunk's vector: count each word in the chunk under its nearest centroid to get a 200-dimensional histogram, then **divide by the chunk's total word count** (including words that are not in the vocabulary, as the PDF requires).
4. Queries are processed the same way; retrieval ranks all 1694 chunks by cosine similarity.

**Improvements**, each changing one switch so its effect can be attributed:

| Switch | Idea |
|---|---|
| `metric=cosine` | Word2Vec similarity is cosine anyway, so spherical k-means is more consistent with it |
| `drop_stopwords` | Words like the/of/and make up a large share of the word count but carry no topic, so they are removed before counting |
| `weighting=idf` | Words that appear in most chunks get a lower weight (the TF-IDF idea applied to the histogram) |
| `soft_top_m=3` | Each word is assigned softly to its 3 nearest centroids by distance, which makes words near cluster boundaries less random |
| `normalize=l2` | For cosine retrieval, L2 normalization fits better than dividing by the word count |
| `append_mean_vector=α` | Appends the mean of the chunk's word vectors (N dimensions) to the histogram: the histogram records which word clusters are used, and the mean records the overall semantic direction |
| K, N, CBOW | Parameter sweeps |

## Results (32 questions, `rag.evaluate.score`, same chunks and questions, directly comparable with the OpenAI baseline)

| Method | hit@1 | hit@4 | hit@10 | MRR |
|---|---|---|---|---|
| OpenAI text-embedding-3-small (C's baseline) | 0.656 | 0.938 | 0.969 | 0.790 |
| BM25 keyword retrieval (reference, not an embedding) | 0.531 | 0.844 | 0.875 | 0.663 |
| **Baseline: the PDF's histogram method** | 0.250 | 0.438 | 0.562 | 0.349 |
| Single: append mean vector, α=0.5 | 0.312 | 0.500 | 0.719 | 0.413 |
| Combined (cosine k-means + stop-word removal + IDF + soft assignment + L2), K=200 | 0.219 | 0.438 | 0.531 | 0.323 |
| Combined, K=400 | 0.312 | 0.656 | 0.688 | 0.455 |
| **Combined, K=400, append mean vector α=1.0 (`BEST`)** | 0.375 | 0.656 | 0.750 | 0.496 |
| Combined, K=400, α=2.0 | 0.406 | 0.625 | 0.781 | 0.526 |

The full table (including the K/N/CBOW sweeps and the hit rank for every question) is in [`evidence/b-part5/results.md`](../evidence/b-part5/results.md), and the plot is `metrics.png`.

**Seed sensitivity.** Word2Vec and k-means are both random, and the corpus has only about 120,000 words (121,307 tokens), so the results are very sensitive to the seed. Across 4 seeds (42, 1, 2, 3): baseline hit@1 = 0.25 / 0.09 / 0.25 / 0.09 and hit@4 = 0.44 / 0.22 / 0.34 / 0.31; BEST hit@1 = 0.38 / 0.31 / 0.28 / 0.28 and hit@4 = 0.66 / 0.56 / 0.53 / 0.50. **BEST beats the baseline on every seed**, and the mean hit@4 rises from 0.33 to 0.56. However, any single number can move 3–10 percentage points by chance, and one of the 32 questions is worth 3.1 percentage points, so no conclusion is drawn about the difference between α=1.0 and α=2.0.

## Observations

- **Why the histogram is far behind OpenAI and BM25.** The histogram drops word identity and keeps only the cluster each word falls into: in a question about the number of OPT months, `opt`, `months`, `12`, and `24` may share a cluster with dozens of other words. BM25 reaches 0.53 precisely through exact word matching, which shows that this task is largely a keyword task.
- **A small K is a disaster, and a very large K does not work either.** With K=50/100, hit@1 drops to 0.06–0.09 (the clusters are too coarse, so all chunks look alike); with K=800 it drops again (the clusters are too fine, so query words and chunk words do not land in the same cluster). K=200–400 is the right range for this corpus.
- **Single improvements barely help; they work only in combination.** Stop-word removal alone is even worse (the questions are short, and removing stop words makes the histogram sparser), but together with IDF, soft assignment, and K=400, hit@4 goes from 0.44 to 0.66. The improvements interact, so they cannot be judged one at a time.
- **Appending the mean vector is the most reliable improvement.** It restores the direction information that the histogram loses and raises hit@10 from 0.56 to 0.72–0.78.
- **Four evaluation questions (4, 12, 13, 23) are missed by every histogram variant**, and OpenAI ranks them only 2nd to 9th. Their wording differs a lot from the sources (for example "cap-gap" and "maximum period of admission"), so they need real semantic understanding, which is the limit of this kind of method.

## How the interface contract is met (`docs/interfaces.md`)

- `fit()` runs once and `embed()` many times; documents and queries share the same saved model. Refitting changes the cluster numbering, so the model is saved in `artifacts/custom_embedding/current` instead of re-clustering on every call.
- The handling of tokenization, unknown words (not in the vocabulary; not counted in the histogram but counted in the baseline's denominator), empty text (returns an all-zero vector), and the normalization denominator is commented in `model.py`.
- The baseline strictly follows the PDF's total-word-count normalization; improvements are recorded separately.
