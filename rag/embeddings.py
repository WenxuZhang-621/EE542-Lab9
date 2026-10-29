"""Official OpenAI embeddings; credentials are loaded locally, never logged."""
import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from shared.config import ROOT


def embedding_model() -> str:
    load_dotenv(ROOT / '.env')
    model = os.getenv('OPENAI_EMBEDDING_MODEL', '').strip()
    if not model:
        raise ValueError('Set OPENAI_EMBEDDING_MODEL in root .env.')
    return model


def official_client() -> OpenAI:
    load_dotenv(ROOT / '.env')
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        raise ValueError('Set OPENAI_API_KEY in root .env. No API call was made.')
    # Lab specifies OpenAI; do not silently redirect to a compatible third party.
    return OpenAI(api_key=key, base_url='https://api.openai.com/v1', timeout=60, max_retries=2)


def embed_texts(texts: list[str], model: str, *, client=None, batch_size: int = 32) -> tuple[np.ndarray, int]:
    if not texts or any(not text.strip() for text in texts):
        raise ValueError('Embedding inputs must be non-empty strings.')
    if batch_size <= 0:
        raise ValueError('batch_size must be positive.')
    if client is None:
        with official_client() as client:
            return embed_texts(texts, model, client=client, batch_size=batch_size)
    vectors = []
    tokens = 0
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        response = client.embeddings.create(model=model, input=batch, encoding_format='float')
        # API records carry their input positions; never rely on response list order.
        data = sorted(response.data, key=lambda item: item.index)
        if [item.index for item in data] != list(range(len(batch))):
            raise ValueError('Embedding response indices do not match inputs.')
        vectors.extend(item.embedding for item in data)
        tokens += response.usage.total_tokens
    matrix = np.asarray(vectors, dtype='float32')
    if matrix.ndim != 2 or matrix.shape[0] != len(texts) or matrix.shape[1] == 0:
        raise ValueError('Invalid embedding response dimensions.')
    if not np.isfinite(matrix).all() or np.any(np.linalg.norm(matrix, axis=1) == 0):
        raise ValueError('Embedding response contains non-finite or zero vectors.')
    return matrix, tokens
