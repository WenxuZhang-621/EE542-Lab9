"""Real rag.api.retrieve() calls against artifacts/indexes/openai (one query embedding each)."""
from rag.api import retrieve

QUESTIONS = [
    'What chunk size should the text splitter use?',
    'How is the custom histogram embedding normalized?',
    'What must the video log demonstrate?',
]
for question in QUESTIONS:
    print(f'Q: {question}')
    for hit in retrieve(question):
        text = ' '.join(hit.chunk.text.split())[:110]
        print(f'  {hit.score:.3f}  p.{hit.chunk.page}  {hit.chunk.chunk_id[:12]}  {text}')
