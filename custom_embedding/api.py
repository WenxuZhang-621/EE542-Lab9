"""Owner B. Baseline histogram and improvements are not implemented yet."""
from typing import List
from shared.contracts import Chunk

def fit(chunks: List[Chunk], n: int, k: int) -> None:
    raise NotImplementedError("B: train Word2Vec, custom clustering, persist centroids")

def embed(text: str) -> List[float]:
    raise NotImplementedError("B: use fitted vocabulary/centroids for normalized histogram")
