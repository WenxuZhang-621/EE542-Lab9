# Step 5: OpenAI connectivity check

2026-10-28 PDT, Wenxu's Mac. The script is `check_openai.py` in this folder (it never prints the key); run it from the repository root with `PYTHONPATH=. .venv/bin/python evidence/c-step5/check_openai.py <stage>`.

| Stage | Result |
|---|---|
| models | The key is valid; 128 models are available, including the embedding models text-embedding-3-small/-3-large/ada-002 |
| embed | text-embedding-3-small, one test text, 1536 dimensions, 5 tokens |
| chat | gpt-6-luna works with Chat Completions; it replied "OK", 11 input / 4 output tokens |

Note: gpt-6-luna does not accept temperature=0 (HTTP 400; only the default value 1 is supported), so the conversation chain must not pass temperature.
Model choice: PDF Part 3 requires OpenAI but does not name a model, so gpt-6-luna was chosen for cost ($0.10/$0.50 per 1M tokens, checked on the OpenAI pricing page on 2026-10-28).
This was only a connectivity check: no final index was built, and no course PDF content was sent.
