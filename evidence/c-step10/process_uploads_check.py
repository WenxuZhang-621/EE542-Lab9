"""Real run of the upload page's processing function: MySQL, chunking, OpenAI index, one question."""
from pathlib import Path
from types import SimpleNamespace
from rag.chain import OpenAIChat, chat_model, create_conversation_chain
from rag.retrieval import VectorStore
from rag.upload_app import process_uploads

FILES = ['data/raw/topic/corpus/sits-ssn.html', 'data/raw/topic/corpus/sits-itin.html',
         'data/raw/part3-demo/lab9-requirements.pdf']
uploads = [SimpleNamespace(name=Path(p).name, getvalue=Path(p).read_bytes) for p in FILES]
report = process_uploads(uploads + [SimpleNamespace(name='notes.docx', getvalue=lambda: b'x')])
for r in report['results']:
    print(r['source'], r['status'], r.get('pages'), r.get('error', ''))
m, i = report['manifest'], report['index']
print(f"chunks {m['chunk_count']} ({m['min_chars']}-{m['max_chars']} chars); index {i['status']} "
      f"{i['count']} x {i['dimension']} {i['model']} -> {report['folder'].name}")
chain = create_conversation_chain(OpenAIChat(chat_model()), VectorStore(report['folder']))
result = chain.ask('How do F-1 students apply for an ITIN?', 'check')
print('Answer:', result.answer)
print('Top sources:', [(h.chunk.source, round(h.score, 3)) for h in result.hits])
