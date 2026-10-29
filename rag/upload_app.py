"""Part 3-I data collection site: upload documents, store them in MySQL, chunk, embed, then ask.

Run with python -m rag.run_upload from the repository root.
"""
import hashlib
import uuid

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from rag.chain import OpenAIChat, chat_model, create_conversation_chain
from rag.chunking import build_chunks
from rag.embeddings import embedding_model
from rag.ingest import ingest_bytes
from rag.retrieval import VectorStore
from rag.storage import get_engine, init_schema
from rag.vectorstore import build_store, chunks_json
from shared.config import CONFIG, project_path

FILE_TYPES = ['pdf', 'txt', 'md', 'html', 'htm']


def process_uploads(files) -> dict:
    """Store each upload in MySQL, chunk the stored versions and embed them into one index."""
    engine = get_engine()
    try:
        init_schema(engine)
        results = [ingest_bytes(engine, file.name, file.getvalue()) for file in files]
        ids = [result['document_id'] for result in results if result['status'] != 'failed']
        if not ids:
            return {'results': results, 'chunks': [], 'manifest': None, 'index': None, 'folder': None}
        chunks, manifest = build_chunks(engine, ids)
    finally:
        engine.dispose()
    # One index per chunk set, as in the CLI, because build_store never overwrites a different index.
    digest = hashlib.sha256(chunks_json(chunks).encode()).hexdigest()
    folder = project_path('indexes') / f'upload-{digest[:12]}'
    index = build_store(chunks, folder, embedding_model())
    return {'results': results, 'chunks': chunks, 'manifest': manifest, 'index': index, 'folder': folder}


def show_report(report: dict) -> None:
    st.subheader('1. Stored in MySQL')
    st.dataframe([{'file': r['source'], 'status': r['status'], 'pages': r.get('pages'),
                   'characters': r.get('characters'), 'error': r.get('error', '')}
                  for r in report['results']], hide_index=True)
    if not report['chunks']:
        st.warning('No document was stored, so nothing was chunked or embedded.')
        return
    manifest, rag = report['manifest'], CONFIG['rag']
    st.subheader('2. Split into chunks')
    st.write(f"{manifest['chunk_count']} chunks of {manifest['min_chars']}–{manifest['max_chars']} characters "
             f"(CharacterTextSplitter, size {rag['chunk_size']}, overlap {rag['chunk_overlap']}).")
    with st.expander('First chunks'):
        for chunk in report['chunks'][:3]:
            page = f' p.{chunk.page}' if chunk.page is not None else ''
            st.caption(f'{chunk.source}{page} · {chunk.chunk_id[:12]}')
            st.text(chunk.text)
    index = report['index']
    st.subheader('3. Embedded with OpenAI')
    st.write(f"{index['count']} vectors, {index['model']}, {index['dimension']} dimensions "
             f"({'reused' if index['status'] == 'unchanged' else 'new index'}).")


def show_hits(hits) -> None:
    with st.expander('Retrieved context'):
        for number, hit in enumerate(hits, start=1):
            page = f' p.{hit.chunk.page}' if hit.chunk.page is not None else ''
            st.caption(f'[{number}] score {hit.score:.3f} · {hit.chunk.source}{page}')
            st.text(hit.chunk.text)


def main():
    st.set_page_config(page_title='Lab9 Document Q&A', page_icon='📄')
    st.title('Document upload and Q&A')
    st.caption('PDF, UTF-8 TXT, Markdown and HTML · 20 MiB per file')
    with st.sidebar:
        files = st.file_uploader('Choose one or more documents', type=FILE_TYPES, accept_multiple_files=True)
        process = st.button('Process documents', disabled=not files)
    if process:
        with st.spinner('Storing, chunking and embedding…'):
            try:
                report = process_uploads(files)
                chain = None
                if report['folder'] is not None:
                    chain = create_conversation_chain(OpenAIChat(chat_model()), VectorStore(report['folder']))
            except SQLAlchemyError:
                # Do not show connection strings or SQL parameters.
                st.error('Database operation failed. Check that MySQL is running and DATABASE_URL in .env.')
                return
            except Exception as exc:
                st.error(f'{type(exc).__name__}: {exc}')
                return
        st.session_state.update(report=report, chain=chain, messages=[],
                                session_id=f'upload-{uuid.uuid4().hex[:8]}')
    report = st.session_state.get('report')
    if report is None:
        st.info('Upload documents in the sidebar, then choose Process documents.')
        return
    show_report(report)
    chain = st.session_state.get('chain')
    if chain is None:
        return
    st.subheader('4. Ask about these documents')
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            if message.get('hits'):
                show_hits(message['hits'])
    question = st.chat_input('Ask a question')
    if question:
        with st.chat_message('user'):
            st.markdown(question)
        try:
            result = chain.ask(question, st.session_state.session_id)
        except Exception as exc:
            st.error(f'{type(exc).__name__}: {exc}')
            return
        with st.chat_message('assistant'):
            st.markdown(result.answer)
            show_hits(result.hits)
        st.session_state.messages += [{'role': 'user', 'content': question},
                                      {'role': 'assistant', 'content': result.answer, 'hits': result.hits}]


if __name__ == '__main__':
    main()
