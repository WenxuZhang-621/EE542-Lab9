"""Owner B. Handoff interface from docs/interfaces.md:

    fit(chunks, n, k)   learn word vectors and centroids from the chunks, persist them
    embed(text)         K-dimensional normalised word histogram from the fitted model

Documents and queries must share one fitted model: fit() runs once per
knowledge base, embed() any number of times. The fitted model is stored under
artifacts/custom_embedding/<name> (git-ignored) and loaded lazily.

    python -m custom_embedding.api fit                    # baseline (N=100, K=200) on the Part 4 chunks
    python -m custom_embedding.api fit --best             # the best configuration from evaluate.py
    python -m custom_embedding.api embed "How many credit hours must an F-1 student take?"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from custom_embedding.model import HistogramConfig, HistogramEmbedder
from shared.config import ROOT, project_path
from shared.contracts import Chunk

MODEL_ROOT = ROOT / "artifacts" / "custom_embedding"
DEFAULT_MODEL = "current"
_model: Optional[HistogramEmbedder] = None


def model_dir(name: str = DEFAULT_MODEL) -> Path:
    return MODEL_ROOT / name


def fit(chunks: List[Chunk], n: int, k: int, config: Optional[HistogramConfig] = None,
        name: str = DEFAULT_MODEL) -> HistogramEmbedder:
    """Train Word2Vec (N dims), cluster the vocabulary into K bins, persist the model."""
    global _model
    cfg = config or HistogramConfig()
    cfg.n, cfg.k = n, k
    _model = HistogramEmbedder(cfg).fit(c.text for c in chunks)
    _model.save(model_dir(name))
    return _model


def load(name: str = DEFAULT_MODEL) -> HistogramEmbedder:
    global _model
    if not (model_dir(name) / "config.json").exists():
        raise RuntimeError(f"no fitted model at {model_dir(name)}: run `python -m custom_embedding.api fit`")
    _model = HistogramEmbedder.load(model_dir(name))
    return _model


def embed(text: str) -> List[float]:
    """Embedding of one text: K bins, plus N values when the model appends the mean word vector."""
    model = _model or load()
    return model.embed(text).tolist()


def load_chunks(path: Path | None = None) -> List[Chunk]:
    path = path or project_path("topic_chunks")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [Chunk(chunk_id=r["chunk_id"], text=r["text"], source=r["source"], page=r.get("page")) for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit", help="fit a histogram model on the Part 4 chunks")
    f.add_argument("--n", type=int, default=100)
    f.add_argument("--k", type=int, default=200)
    f.add_argument("--best", action="store_true", help="use the best configuration found by evaluate.py")
    f.add_argument("--name", default=DEFAULT_MODEL)
    e = sub.add_parser("embed", help="print the embedding of a text with the fitted model")
    e.add_argument("text")
    e.add_argument("--name", default=DEFAULT_MODEL)
    args = ap.parse_args()
    if args.cmd == "fit":
        cfg = None
        if args.best:
            from custom_embedding.evaluate import BEST
            cfg, args.n, args.k = BEST, BEST.n, BEST.k
        m = fit(load_chunks(), args.n, args.k, config=cfg, name=args.name)
        print(json.dumps({"model": str(model_dir(args.name)), "config": m.config.name(), **m.train_stats}, indent=2))
    else:
        m = load(args.name)
        v = m.embed(args.text)
        k = m.config.k
        nz = [(int(i), round(float(v[i]), 4)) for i in v[:k].nonzero()[0]]
        print(f"dimension {v.size} ({k} histogram bins{' + mean vector' if v.size > k else ''}), "
              f"non-zero bins {len(nz)}, bin sum {v[:k].sum():.4f}")
        for i, w in sorted(nz, key=lambda t: -t[1])[:8]:
            print(f"  bin {i:4d}  {w:.4f}  nearest words: {' '.join(m.cluster_words(i, 6))}")


if __name__ == "__main__":
    main()
