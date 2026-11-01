"""Opt in: LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v."""
import os
import unittest
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import event, select, func
from sqlalchemy.exc import SQLAlchemyError
from rag.documents import DocumentPage
from rag.storage import get_engine, init_schema, save_document, documents, pages


@unittest.skipUnless(os.getenv('LAB9_TEST_MYSQL') == '1', 'explicit MySQL opt-in required')
class MySQLStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine()
        init_schema(self.engine)
        self.source = 'test-' + uuid4().hex

    def tearDown(self):
        # Delete only records created by this test's unique source, never lab inputs.
        with self.engine.begin() as conn:
            ids = select(documents.c.document_id).where(documents.c.source == self.source)
            conn.execute(pages.delete().where(pages.c.document_id.in_(ids)))
            conn.execute(documents.delete().where(documents.c.source == self.source))
        self.engine.dispose()

    def test_roundtrip_duplicate_and_new_version(self):
        original = [DocumentPage(self.source, 1, 'Café, naïve – RAG source text'), DocumentPage(self.source, 2, '')]
        first = save_document(self.engine, self.source, b'version1', original)
        second = save_document(self.engine, self.source, b'version1', original)
        third = save_document(self.engine, self.source, b'version2', original)
        self.assertEqual([first['status'], second['status'], third['status']], ['inserted','skipped','inserted'])
        self.assertNotEqual(first['document_id'], third['document_id'])
        with self.engine.connect() as conn:
            text = conn.execute(select(pages.c.text).where(pages.c.document_id == first['document_id']).order_by(pages.c.ordinal)).scalars().all()
            self.assertEqual(text, [p.text for p in original])

    def test_failure_rolls_back_document_and_pages(self):
        def fail_page_insert(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith('INSERT INTO rag_document_pages'):
                raise SQLAlchemyError('Injected page-write failure')
        event.listen(self.engine, 'before_cursor_execute', fail_page_insert)
        try:
            with self.assertRaises(SQLAlchemyError):
                save_document(self.engine, self.source, b'rollback', [DocumentPage(self.source, 1, 'test')])
        finally:
            event.remove(self.engine, 'before_cursor_execute', fail_page_insert)
        with self.engine.connect() as conn:
            count = conn.execute(select(func.count()).select_from(documents).where(documents.c.source == self.source)).scalar_one()
            self.assertEqual(count, 0)

    def test_empty_document_rejected(self):
        with self.assertRaises(ValueError):
            save_document(self.engine, self.source, b'blank', [DocumentPage(self.source, 1, '')])
