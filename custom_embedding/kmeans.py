"""K-means written from scratch (Part 5 asks for custom clustering code).

Lloyd's algorithm with k-means++ seeding. Two distance options:
  euclidean  - standard k-means on the raw word vectors
  cosine     - spherical k-means: vectors and centroids are unit-normalised,
               distance = 1 - cosine similarity. Word2Vec similarity is cosine
               similarity, so this matches how the vectors were trained.
Only NumPy is used.
"""
from dataclasses import dataclass
import numpy as np


def _normalize_rows(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms


def pairwise_sq_dist(x: np.ndarray, c: np.ndarray) -> np.ndarray:
    """||x_i - c_j||^2 for every pair, via the expansion a^2 - 2ab + b^2 (no Python loops)."""
    xx = np.einsum("ij,ij->i", x, x)[:, None]
    cc = np.einsum("ij,ij->i", c, c)[None, :]
    d = xx - 2.0 * x @ c.T + cc
    np.maximum(d, 0.0, out=d)  # rounding can make tiny negatives
    return d


@dataclass
class KMeansResult:
    centroids: np.ndarray      # (k, n)
    labels: np.ndarray         # (num_points,)
    inertia: float             # sum of squared distances to the assigned centroid
    iterations: int
    metric: str


def kmeans_pp_init(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++: each new centre is drawn with probability proportional to its
    squared distance from the nearest existing centre, so centres spread out
    instead of landing in one dense region."""
    n_points = x.shape[0]
    centroids = np.empty((k, x.shape[1]), dtype=x.dtype)
    centroids[0] = x[rng.integers(n_points)]
    closest = pairwise_sq_dist(x, centroids[:1])[:, 0]
    for j in range(1, k):
        probs = closest / closest.sum() if closest.sum() > 0 else np.full(n_points, 1.0 / n_points)
        idx = rng.choice(n_points, p=probs)
        centroids[j] = x[idx]
        closest = np.minimum(closest, pairwise_sq_dist(x, centroids[j:j + 1])[:, 0])
    return centroids


def kmeans(x: np.ndarray, k: int, metric: str = "euclidean", max_iter: int = 100,
           tol: float = 1e-4, seed: int = 42) -> KMeansResult:
    if metric not in ("euclidean", "cosine"):
        raise ValueError("metric must be euclidean or cosine")
    if k <= 0 or k > x.shape[0]:
        raise ValueError(f"k must be in 1..{x.shape[0]}")
    x = np.asarray(x, dtype=np.float32)
    if metric == "cosine":
        x = _normalize_rows(x)
    rng = np.random.default_rng(seed)
    centroids = kmeans_pp_init(x, k, rng)
    labels = np.zeros(x.shape[0], dtype=np.int64)
    inertia = np.inf
    for iteration in range(1, max_iter + 1):
        d = pairwise_sq_dist(x, centroids)
        labels = d.argmin(axis=1)
        new_inertia = float(d[np.arange(x.shape[0]), labels].sum())
        # Recompute centres as the mean of their members. An empty cluster
        # takes the point farthest from its centre so k stays constant.
        new_centroids = np.zeros_like(centroids)
        counts = np.bincount(labels, minlength=k)
        np.add.at(new_centroids, labels, x)
        empty = counts == 0
        nonempty = ~empty
        new_centroids[nonempty] /= counts[nonempty, None]
        if empty.any():
            farthest = np.argsort(d[np.arange(x.shape[0]), labels])[::-1][: empty.sum()]
            new_centroids[empty] = x[farthest]
        if metric == "cosine":
            new_centroids = _normalize_rows(new_centroids)
        shift = float(np.abs(new_centroids - centroids).max())
        centroids = new_centroids
        if inertia - new_inertia <= tol * max(inertia, 1.0) and shift <= tol:
            inertia = new_inertia
            break
        inertia = new_inertia
    return KMeansResult(centroids=centroids, labels=labels, inertia=inertia,
                        iterations=iteration, metric=metric)


def assign(x: np.ndarray, centroids: np.ndarray, metric: str = "euclidean") -> np.ndarray:
    """Nearest centroid for each row of x (used at embedding time)."""
    x = np.asarray(x, dtype=np.float32)
    if metric == "cosine":
        x = _normalize_rows(x)
    return pairwise_sq_dist(x, centroids).argmin(axis=1)


def soft_assign(x: np.ndarray, centroids: np.ndarray, metric: str, top_m: int,
                temperature: float) -> tuple[np.ndarray, np.ndarray]:
    """Weights over the top_m nearest centroids, softmax(-distance / temperature).
    Returns (indices (num, top_m), weights (num, top_m)); weights sum to 1 per row."""
    x = np.asarray(x, dtype=np.float32)
    if metric == "cosine":
        x = _normalize_rows(x)
    d = pairwise_sq_dist(x, centroids)
    idx = np.argpartition(d, min(top_m, d.shape[1] - 1), axis=1)[:, :top_m]
    dd = np.take_along_axis(d, idx, axis=1)
    logits = -dd / max(temperature, 1e-8)
    logits -= logits.max(axis=1, keepdims=True)
    w = np.exp(logits)
    w /= w.sum(axis=1, keepdims=True)
    return idx, w
