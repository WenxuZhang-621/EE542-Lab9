# Step 4 offline verification

2026-10-28: offline tests only, exit code 0. Command: python -m unittest discover -s tests -p test_vectorstore.py -v.
The tests use mocked API responses and small synthetic vectors and do not call OpenAI. The test folder is cleaned up automatically, and no final index was published.
Covered: response order and batching, indexes in error responses, normalized cosine ranking, save/reload and the chunk mapping, repeated builds, rejection of a changed model, corruption detection, no publish when the API fails, and rejection of zero vectors.
Still to be verified after this step: the real key and model configuration, and semantic retrieval quality. SDK and library versions are in rag/requirements.txt.
