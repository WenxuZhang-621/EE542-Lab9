"""Connectivity check for the Lab9 OpenAI config. Never prints the key."""
import os
import re
import sys

from dotenv import load_dotenv
from openai import OpenAI
from shared.config import ROOT

load_dotenv(ROOT / ".env")
key = os.getenv("OPENAI_API_KEY", "").strip()
emb_model = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip()
chat_model = os.getenv("OPENAI_CHAT_MODEL", "").strip()


def safe(msg: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_\-*]+", "sk-<redacted>", str(msg))


print("OPENAI_API_KEY:", "set" if key else "EMPTY")
print("OPENAI_EMBEDDING_MODEL:", emb_model or "EMPTY")
print("OPENAI_CHAT_MODEL:", chat_model or "EMPTY")
if not key:
    sys.exit(1)

stage = sys.argv[1] if len(sys.argv) > 1 else "env"
if stage == "env":
    sys.exit(0)

client = OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=30, max_retries=1)
try:
    if stage == "models":
        ids = sorted(m.id for m in client.models.list())
        print("models available:", len(ids))
        print("embedding:", [i for i in ids if "embedding" in i])
        chat = [i for i in ids if i.startswith(("gpt-", "o")) and not any(
            t in i for t in ("audio", "realtime", "tts", "transcribe", "image", "search", "embedding"))]
        print("chat-like:", chat)
    elif stage == "embed":
        from rag.embeddings import embed_texts
        vectors, tokens = embed_texts(["Lab9 connectivity test."], emb_model, client=client)
        print("embedding ok: model", emb_model, "dimension", vectors.shape[1], "tokens", tokens)
    elif stage == "chat":
        messages = [{"role": "user", "content": "Reply with exactly: OK"}]
        try:
            r = client.chat.completions.create(model=chat_model, messages=messages,
                                               temperature=0, max_completion_tokens=20)
            print("temperature=0 accepted")
        except Exception as exc:
            print("temperature=0 rejected:", type(exc).__name__, safe(exc))
            r = client.chat.completions.create(model=chat_model, messages=messages,
                                               max_completion_tokens=200)
        print("chat ok: model", r.model, "| reply:", repr(r.choices[0].message.content),
              "| finish:", r.choices[0].finish_reason, "| usage:", r.usage.prompt_tokens,
              "in /", r.usage.completion_tokens, "out")
except Exception as exc:  # report type and redacted message only
    print("FAILED:", type(exc).__name__, safe(exc))
    sys.exit(2)
