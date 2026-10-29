"""Step 1: upload and inspect source text; not a complete RAG application."""
import streamlit as st

from rag.documents import extract_pages


def main():
    st.set_page_config(page_title='Lab9 Document Reader', page_icon='📄')
    st.title('Document upload and text preview')
    st.caption('PDF, UTF-8 TXT and Markdown · 20 MiB per file')
    st.info('Step 1: inspect source text. Database storage, chunking and Q&A come next.')
    with st.sidebar:
        files = st.file_uploader(
            'Choose one or more documents',
            type=['pdf', 'txt', 'md'],
            accept_multiple_files=True,
        )
        process = st.button('Extract text', disabled=not files)
    if not process:
        return
    for uploaded in files:
        st.subheader(uploaded.name)
        try:
            pages = extract_pages(uploaded.name, uploaded.getvalue())
        except Exception as exc:
            # Isolate failures: one malformed document must not hide the next one.
            st.error(f'{type(exc).__name__}: {exc}')
            continue
        st.write(f'{len(pages)} page(s) / {sum(len(p.text) for p in pages)} characters')
        if not pages:
            st.warning('This document contains no pages.')
        for page in pages:
            label = f'Page {page.page}' if page.page is not None else 'Text document'
            with st.expander(label, expanded=len(pages) == 1):
                if not page.text.strip():
                    st.warning('No text extracted. A scanned page may need OCR, which is not implemented.')
                else:
                    st.text(page.text)


if __name__ == '__main__':
    main()
