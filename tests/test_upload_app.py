"""Upload page rendering with an injected report; no MySQL or OpenAI calls."""
import unittest
from streamlit.testing.v1 import AppTest
from shared.config import ROOT
from shared.contracts import Chunk

APP = str(ROOT / 'rag/upload_app.py')


class UploadAppTests(unittest.TestCase):
    def test_initial_page_waits_for_files(self):
        app = AppTest.from_file(APP).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn('Upload documents in the sidebar', app.info[0].value)
        self.assertTrue(app.sidebar.button[0].disabled)

    def test_report_shows_storage_chunks_and_index(self):
        app = AppTest.from_file(APP)
        app.session_state['report'] = {
            'results': [{'source': 'a.pdf', 'status': 'inserted', 'pages': 2, 'characters': 900},
                        {'source': 'b.docx', 'status': 'failed', 'error': 'Supported formats'}],
            'chunks': [Chunk('c1', 'first chunk text', 'a.pdf', 1)],
            'manifest': {'chunk_count': 1, 'min_chars': 16, 'max_chars': 16},
            'index': {'status': 'created', 'count': 1, 'model': 'test-model', 'dimension': 2},
            'folder': None,
        }
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([s.value for s in app.subheader],
                         ['1. Stored in MySQL', '2. Split into chunks', '3. Embedded with OpenAI'])
        self.assertIn('1 vectors, test-model, 2 dimensions (new index)', app.markdown[-1].value)

    def test_nothing_stored_shows_warning(self):
        app = AppTest.from_file(APP)
        app.session_state['report'] = {'results': [{'source': 'b.docx', 'status': 'failed', 'error': 'x'}],
                                       'chunks': [], 'manifest': None, 'index': None, 'folder': None}
        app.run(timeout=30)
        self.assertIn('nothing was chunked', app.warning[0].value)
