"""Topic data curation and evaluation scoring; no network, MySQL or OpenAI calls."""
import unittest
from unittest.mock import patch
from rag.documents import DocumentPage
from rag.evaluate import label, score
from rag.ingest import ingest_bytes
from rag.topic_data import check_type, clean_irs_pdf, ecfr_paragraph
from shared.contracts import Chunk


class CurationTests(unittest.TestCase):
    def test_ecfr_keeps_one_paragraph_as_plain_text(self):
        xml = ('<DIV8><P>(e) <I>Traders</I> text.</P><P>(f) <I>Students</I>&#x2014;rules.</P>'
               '<TABLE><TR><TD>(1)</TD><TD>Admission</TD></TR></TABLE><P>(2) [Reserved]</P>'
               '<P>(g) <I>Other</I></P></DIV8>')
        self.assertEqual(ecfr_paragraph(xml, 'f', 'g'), '(f) Students—rules.\n(1) | Admission')

    def test_irs_cleanup_removes_proof_header_and_artifacts(self):
        page = ('Userid: CPM Page 2 of 95\nMUST be removed before printing.\n'
                'Y ou must file Form W -4 for territo-\nrial self -employment.')
        with patch('rag.topic_data.extract_pages', return_value=[DocumentPage('x', 1, page), DocumentPage('x', 2, 'B')]):
            self.assertEqual(clean_irs_pdf(b'%PDF'),
                             'You must file Form W-4 for territorial self-employment.\fB')

    def test_error_pages_are_not_saved_as_documents(self):
        with self.assertRaises(ValueError):
            check_type('irs-p519.pdf', b'<!DOCTYPE html><title>Page Not Found</title>')
        check_type('irs-p519.pdf', b'%PDF-1.7')
        check_type('page.html', b'\n<!DOCTYPE html>')


class IngestBytesTests(unittest.TestCase):
    def test_bad_files_become_failed_rows_without_database(self):
        self.assertEqual(ingest_bytes(None, 'notes.docx', b'x')['status'], 'failed')
        self.assertIn('Supported formats', ingest_bytes(None, 'notes.docx', b'x')['error'])


class EvaluationTests(unittest.TestCase):
    def test_label_matches_any_evidence_phrase(self):
        chunks = [Chunk('a', 'Students may not accrue an aggregate of more  than 90 days.', 's'),
                  Chunk('b', 'Unrelated text.', 's'), Chunk('c', 'Up to 90 days of unemployment.', 's')]
        drafts = [{'area': 'work', 'question': 'Q', 'evidence': ['aggregate of more than 90 days', 'UP TO 90 DAYS']}]
        self.assertEqual(label(drafts, chunks)[0]['relevant_chunk_ids'], ['a', 'c'])
        with self.assertRaises(ValueError):
            label([{'area': 'x', 'question': 'Q2', 'evidence': ['missing']}], chunks)

    def test_score_hits_recall_and_mrr(self):
        questions = [{'question': 'Q1', 'relevant_chunk_ids': ['a', 'b']},
                     {'question': 'Q2', 'relevant_chunk_ids': ['z']}]
        result = score(questions, [['x', 'a', 'b'], ['x', 'y']], ks=(1, 2))
        self.assertEqual(result['summary'], {'hit@1': 0.0, 'hit@2': 0.5, 'recall@1': 0.0,
                                             'recall@2': 0.25, 'mrr': 0.25})
        self.assertEqual([row['first_relevant_rank'] for row in result['per_question']], [2, None])
