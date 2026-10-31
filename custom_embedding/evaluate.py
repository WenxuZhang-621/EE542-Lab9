"""Part 5 experiments: the handout baseline and each improvement, scored like the OpenAI baseline.

    python -m custom_embedding.evaluate                 # run every configuration
    python -m custom_embedding.evaluate --only baseline # one group (baseline | sweep | improve | hybrid)

Writes evidence/b-part5/results.json (every run: config, training stats, metrics,
per-question ranks), results.md (comparison table) and metrics.png. Rankings use
cosine similarity between the query histogram and every chunk histogram over all
1,694 chunks of data/topic/index, the same set and the same metrics
(rag.evaluate.score) as data/topic/baseline_openai.json.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import math
import time

import numpy as np

from custom_embedding.api import load_chunks
from custom_embedding.model import HistogramConfig, HistogramEmbedder, cosine_rankings
from custom_embedding.tokenize import tokenize
from rag.evaluate import read_jsonl, score
from shared.config import ROOT, project_path

OUT = ROOT / "evidence" / "b-part5"
TOP = 10

BASELINE = HistogramConfig()  # N=100, K=200, euclidean, count, total_words: the handout's method
COMBINED = replace(BASELINE, metric="cosine", drop_stopwords=True, weighting="idf", soft_top_m=3, normalize="l2")
# Best configuration found by the grid below (see evidence/b-part5/results.md); used by `api fit --best`.
BEST = replace(COMBINED, k=400, append_mean_vector=1.0)


def experiments(only: str | None):
    """(group, label, config). Each improvement changes one thing against the baseline
    so its effect is attributable; the last group combines the ones that helped."""
    runs = [("baseline", "baseline (handout)", BASELINE)]
    runs += [("sweep", f"K={k}", replace(BASELINE, k=k)) for k in (50, 100, 400, 800)]
    runs += [("sweep", f"N={n}", replace(BASELINE, n=n)) for n in (50, 200)]
    runs += [("sweep", "CBOW instead of skip-gram", replace(BASELINE, sg=0))]
    runs += [
        ("improve", "cosine (spherical) k-means", replace(BASELINE, metric="cosine")),
        ("improve", "drop stop-words", replace(BASELINE, drop_stopwords=True)),
        ("improve", "IDF-weighted bins", replace(BASELINE, weighting="idf")),
        ("improve", "soft assignment (3 centroids)", replace(BASELINE, soft_top_m=3)),
        ("improve", "L2 normalisation", replace(BASELINE, normalize="l2")),
        ("improve", "+ mean word vector (alpha 0.5)", replace(BASELINE, append_mean_vector=0.5)),
        ("improve", "+ mean word vector (alpha 1.0)", replace(BASELINE, append_mean_vector=1.0)),
        ("improve", "+ mean word vector (alpha 2.0)", replace(BASELINE, append_mean_vector=2.0)),
    ]
    runs += [
        ("hybrid", "combined improvements", COMBINED),
        ("hybrid", "combined, K=400", replace(COMBINED, k=400)),
        ("hybrid", "combined, K=400, + mean vector 0.5", replace(COMBINED, k=400, append_mean_vector=0.5)),
        ("hybrid", "combined, K=400, + mean vector 1.0 (BEST)", BEST),
        ("hybrid", "combined, K=400, + mean vector 2.0", replace(COMBINED, k=400, append_mean_vector=2.0)),
        ("hybrid", "combined, K=800, + mean vector 1.0", replace(BEST, k=800)),
    ]
    # Seed sensitivity: Word2Vec and k-means are stochastic; with 32 questions one question is 3.1 points of hit@k.
    runs += [("seeds", f"baseline, seed {sd}", replace(BASELINE, seed=sd)) for sd in (1, 2, 3)]
    runs += [("seeds", f"BEST, seed {sd}", replace(BEST, seed=sd)) for sd in (1, 2, 3)]
    return [r for r in runs if only is None or r[0] == only]


def bm25_reference(chunks, questions) -> dict:
    """Lexical reference point (not an embedding): BM25 over the same tokens.
    Shows how much of the task is plain keyword overlap."""
    docs = [tokenize(c.text, drop_stopwords=True) for c in chunks]
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + (n_docs - n + 0.5) / (n + 0.5)) for t, n in df.items()}
    k1, b = 1.5, 0.75
    tfs = [{t: d.count(t) for t in set(d)} for d in docs]
    rankings = []
    for q in questions:
        qt = tokenize(q["question"], drop_stopwords=True)
        scores = np.zeros(n_docs)
        for i, (tf, d) in enumerate(zip(tfs, docs)):
            s = 0.0
            for t in qt:
                if t in tf:
                    f = tf[t]
                    s += idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avgdl))
            scores[i] = s
        order = np.argsort(-scores)[:TOP]
        rankings.append([chunks[j].chunk_id for j in order])
    return score(questions, rankings)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["baseline", "sweep", "improve", "hybrid", "seeds"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks()
    questions = read_jsonl(project_path("questions"))
    ids = [c.chunk_id for c in chunks]
    openai = json.loads((ROOT / "data/topic/baseline_openai.json").read_text())
    assert openai["questions"] == len(questions)

    results = []
    if args.only is None:
        t0 = time.time()
        bm = bm25_reference(chunks, questions)
        results.append({"group": "reference", "label": "BM25 keyword search (not an embedding)",
                        "config": None, "stats": None, "seconds": round(time.time() - t0, 1), **bm})
        print(f"{'BM25 reference':45s} {bm['summary']}")

    for group, label, cfg in experiments(args.only):
        t0 = time.time()
        model = HistogramEmbedder(cfg).fit(c.text for c in chunks)
        doc_vectors = model.embed_many(c.text for c in chunks)
        query_vectors = model.embed_many(q["question"] for q in questions)
        rankings = cosine_rankings(doc_vectors, query_vectors, ids, TOP)
        res = score(questions, rankings)
        empty_queries = int((np.abs(query_vectors).sum(axis=1) == 0).sum())
        results.append({"group": group, "label": label, "config": asdict(cfg), "name": cfg.name(),
                        "stats": model.train_stats, "empty_query_vectors": empty_queries,
                        "seconds": round(time.time() - t0, 1), **res})
        print(f"{label:45s} {res['summary']}  ({time.time() - t0:.0f}s)")

    out = {"created_at": datetime.now(timezone.utc).isoformat(), "chunks": len(chunks),
           "index_chunks_sha256": openai["index_chunks_sha256"], "questions": len(questions),
           "openai_baseline": {"model": openai["model"], "summary": openai["summary"]},
           "runs": results}
    (OUT / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    write_markdown(out)
    try:
        plot(out)
    except ImportError:
        pass
    print("->", OUT)


def write_markdown(out: dict) -> None:
    lines = ["# Part 5: word-histogram embedding vs OpenAI embedding", "",
             f"Chunks: {out['chunks']} (data/topic/index), questions: {out['questions']}, metrics from "
             "`rag.evaluate.score`. Rankings by cosine similarity over all chunks; k-means and Word2Vec seeded (42).", "",
             "| Group | Method | hit@1 | hit@4 | hit@10 | recall@4 | recall@10 | MRR | vocab | fit+embed s |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    s = out["openai_baseline"]["summary"]
    lines.append(f"| reference | OpenAI {out['openai_baseline']['model']} (C's baseline) | {s['hit@1']:.3f} | {s['hit@4']:.3f} | "
                 f"{s.get('hit@10', float('nan')):.3f} | {s.get('recall@4', float('nan')):.3f} | {s.get('recall@10', float('nan')):.3f} | "
                 f"{s.get('mrr', float('nan')):.3f} | – | – |")
    for r in out["runs"]:
        s = r["summary"]
        vocab = r["stats"]["vocabulary"] if r.get("stats") else "–"
        lines.append(f"| {r['group']} | {r['label']} | {s['hit@1']:.3f} | {s['hit@4']:.3f} | {s['hit@10']:.3f} | "
                     f"{s['recall@4']:.3f} | {s['recall@10']:.3f} | {s['mrr']:.3f} | {vocab} | {r['seconds']} |")
    # Which questions each key method gets right at rank 1 / within 4: shows that the methods fail on different questions.
    keys = [r for r in out["runs"] if r["label"] in ("baseline (handout)", "BM25 keyword search (not an embedding)")
            or "(BEST)" in r["label"]]
    if keys:
        lines += ["", "## Per-question first relevant rank (OpenAI / BM25 / baseline / BEST)", "",
                  "| # | Question | OpenAI | BM25 | baseline | BEST |", "|---|---|---|---|---|---|"]
        openai_ranks = {}
        try:
            import json as _json
            from shared.config import ROOT as _ROOT
            for row in _json.loads((_ROOT / "data/topic/baseline_openai.json").read_text())["per_question"]:
                openai_ranks[row["question"]] = row["first_relevant_rank"]
        except Exception:
            pass
        by_label = {r["label"]: {q["question"]: q["first_relevant_rank"] for q in r["per_question"]} for r in keys}
        bm = by_label.get("BM25 keyword search (not an embedding)", {})
        base = by_label.get("baseline (handout)", {})
        best = next((v for k, v in by_label.items() if "(BEST)" in k), {})
        fmt = lambda r: "–" if r is None else str(r)
        for i, q in enumerate(base or best, 1):
            lines.append(f"| {i} | {q[:70]} | {fmt(openai_ranks.get(q))} | {fmt(bm.get(q))} | {fmt(base.get(q))} | {fmt(best.get(q))} |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n")


def plot(out: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = ["OpenAI"] + [r["label"] for r in out["runs"]]
    h1 = [out["openai_baseline"]["summary"]["hit@1"]] + [r["summary"]["hit@1"] for r in out["runs"]]
    h4 = [out["openai_baseline"]["summary"]["hit@4"]] + [r["summary"]["hit@4"] for r in out["runs"]]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(labels) + 1.5))
    ax.barh(y - 0.2, h1, 0.4, label="hit@1")
    ax.barh(y + 0.2, h4, 0.4, label="hit@4")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("fraction of the 32 questions")
    ax.set_title("Retrieval quality of each embedding on the F-1 knowledge base")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "metrics.png", dpi=150)


if __name__ == "__main__":
    main()
