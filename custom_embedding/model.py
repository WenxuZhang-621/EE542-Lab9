"""Word-histogram embedding (Part 5): Word2Vec -> custom k-means -> normalised histogram.

Baseline, as the handout specifies:
  1. Word2Vec gives every word in the corpus an N-dimensional vector.
  2. Custom k-means groups the words into K clusters with K centroid vectors.
  3. A chunk's embedding is a K-dimensional histogram: each word of the chunk
     falls into the bin of its nearest centroid; the histogram is divided by
     the total number of words in the chunk.

Improvements are switches on HistogramConfig, so every variant shares the same
tokeniser, word vectors and evaluation. Fitted parameters (vocabulary,
word vectors, centroids, IDF) are saved so that documents and queries are
embedded with the same model; refitting on each call would change the bins.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np

from custom_embedding.kmeans import assign, kmeans, soft_assign
from custom_embedding.tokenize import tokenize


@dataclass
class HistogramConfig:
    n: int = 100                 # Word2Vec dimension
    k: int = 200                 # number of clusters / histogram bins
    window: int = 5
    min_count: int = 2           # words seen fewer times get no vector (unknown at embed time)
    epochs: int = 30
    sg: int = 1                  # 1 = skip-gram, 0 = CBOW
    metric: str = "euclidean"    # distance used for clustering and binning
    drop_stopwords: bool = False
    min_length: int = 1
    weighting: str = "count"     # count | idf
    soft_top_m: int = 1          # 1 = hard assignment; >1 = soft assignment over m centroids
    soft_temperature: float = 0.05
    normalize: str = "total_words"  # total_words (PDF) | binned_words | l2
    append_mean_vector: float = 0.0  # >0: concatenate alpha * mean word vector (N dims) to the histogram
    seed: int = 42

    def name(self) -> str:
        parts = [f"N{self.n}", f"K{self.k}", self.metric, self.weighting, self.normalize]
        if self.drop_stopwords:
            parts.append("nostop")
        if self.soft_top_m > 1:
            parts.append(f"soft{self.soft_top_m}")
        if self.append_mean_vector:
            parts.append(f"mean{self.append_mean_vector:g}")
        return "-".join(parts)


class HistogramEmbedder:
    def __init__(self, config: HistogramConfig):
        self.config = config
        self.vocab: Dict[str, int] = {}
        self.vectors: Optional[np.ndarray] = None     # (V, N)
        self.centroids: Optional[np.ndarray] = None   # (K, N)
        self.word_bin: Optional[np.ndarray] = None    # (V,) hard bin per vocabulary word
        self.idf: Optional[np.ndarray] = None         # (V,)
        self.train_stats: dict = {}

    # ------------------------------------------------------------------ fit
    def _tokens(self, text: str) -> List[str]:
        return tokenize(text, self.config.drop_stopwords, self.config.min_length)

    def fit(self, texts: Iterable[str]) -> "HistogramEmbedder":
        from gensim.models import Word2Vec  # imported here so embed() works without gensim

        cfg = self.config
        sentences = [self._tokens(t) for t in texts]
        w2v = Word2Vec(sentences, vector_size=cfg.n, window=cfg.window, min_count=cfg.min_count,
                       sg=cfg.sg, epochs=cfg.epochs, seed=cfg.seed, workers=1)  # workers=1: deterministic
        words = list(w2v.wv.index_to_key)
        self.vocab = {w: i for i, w in enumerate(words)}
        self.vectors = np.asarray(w2v.wv[words], dtype=np.float32)

        result = kmeans(self.vectors, cfg.k, metric=cfg.metric, seed=cfg.seed)
        self.centroids = result.centroids
        self.word_bin = result.labels

        # IDF over chunks: words that appear in most chunks carry little information.
        df = np.zeros(len(words), dtype=np.float64)
        for toks in sentences:
            for i in {self.vocab[t] for t in toks if t in self.vocab}:
                df[i] += 1
        n_docs = len(sentences)
        self.idf = np.log((1 + n_docs) / (1 + df)) + 1.0

        total = sum(len(s) for s in sentences)
        known = sum(1 for s in sentences for t in s if t in self.vocab)
        self.train_stats = {"documents": n_docs, "tokens": total, "vocabulary": len(words),
                            "token_coverage": round(known / max(total, 1), 4),
                            "kmeans_iterations": result.iterations, "kmeans_inertia": round(result.inertia, 3),
                            "cluster_sizes_min": int(np.bincount(result.labels, minlength=cfg.k).min()),
                            "cluster_sizes_max": int(np.bincount(result.labels, minlength=cfg.k).max())}
        return self

    # ---------------------------------------------------------------- embed
    def embed(self, text: str) -> np.ndarray:
        if self.centroids is None:
            raise RuntimeError("fit() or load() first")
        cfg = self.config
        toks = self._tokens(text)
        idx = np.array([self.vocab[t] for t in toks if t in self.vocab], dtype=np.int64)
        hist = np.zeros(cfg.k, dtype=np.float32)
        if idx.size:
            weights = self.idf[idx].astype(np.float32) if cfg.weighting == "idf" else np.ones(idx.size, np.float32)
            if cfg.soft_top_m <= 1:
                np.add.at(hist, self.word_bin[idx], weights)
            else:
                bins, w = soft_assign(self.vectors[idx], self.centroids, cfg.metric,
                                      cfg.soft_top_m, cfg.soft_temperature)
                np.add.at(hist, bins.ravel(), (w * weights[:, None]).ravel())
        # Normalisation. The handout divides by the total number of words in the chunk.
        if cfg.normalize == "total_words":
            hist /= max(len(toks), 1)
        elif cfg.normalize == "binned_words":
            hist /= max(float(hist.sum()), 1e-12) if idx.size else 1.0
        elif cfg.normalize == "l2":
            hist /= max(float(np.linalg.norm(hist)), 1e-12)
        else:
            raise ValueError(cfg.normalize)
        if cfg.append_mean_vector > 0:
            mean = self.vectors[idx].mean(axis=0) if idx.size else np.zeros(cfg.n, np.float32)
            mean = mean / max(float(np.linalg.norm(mean)), 1e-12)
            hist = np.concatenate([hist, cfg.append_mean_vector * mean]).astype(np.float32)
        return hist

    def embed_many(self, texts: Iterable[str]) -> np.ndarray:
        return np.stack([self.embed(t) for t in texts])

    # --------------------------------------------------------------- persist
    def save(self, folder: Path) -> None:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "config.json").write_text(json.dumps(asdict(self.config), indent=2))
        (folder / "vocab.json").write_text(json.dumps(list(self.vocab), ensure_ascii=False))
        (folder / "stats.json").write_text(json.dumps(self.train_stats, indent=2))
        np.savez_compressed(folder / "model.npz", vectors=self.vectors, centroids=self.centroids,
                            word_bin=self.word_bin, idf=self.idf)

    @classmethod
    def load(cls, folder: Path) -> "HistogramEmbedder":
        folder = Path(folder)
        model = cls(HistogramConfig(**json.loads((folder / "config.json").read_text())))
        words = json.loads((folder / "vocab.json").read_text())
        model.vocab = {w: i for i, w in enumerate(words)}
        data = np.load(folder / "model.npz")
        model.vectors, model.centroids = data["vectors"], data["centroids"]
        model.word_bin, model.idf = data["word_bin"], data["idf"]
        model.train_stats = json.loads((folder / "stats.json").read_text())
        return model

    # ------------------------------------------------------------ inspection
    def cluster_words(self, bin_index: int, top: int = 12) -> List[str]:
        """Words closest to a centroid, for showing what a histogram bin means."""
        members = np.where(self.word_bin == bin_index)[0]
        if members.size == 0:
            return []
        d = ((self.vectors[members] - self.centroids[bin_index]) ** 2).sum(axis=1)
        inv = {i: w for w, i in self.vocab.items()}
        return [inv[int(members[j])] for j in np.argsort(d)[:top]]


def cosine_rankings(doc_vectors: np.ndarray, query_vectors: np.ndarray, doc_ids: List[str],
                    top: int = 10) -> List[List[str]]:
    """Rank documents for each query by cosine similarity; returns chunk-ID lists."""
    def norm(x):
        n = np.linalg.norm(x, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return x / n
    sims = norm(query_vectors) @ norm(doc_vectors).T
    order = np.argsort(-sims, axis=1)[:, :top]
    return [[doc_ids[j] for j in row] for row in order]
