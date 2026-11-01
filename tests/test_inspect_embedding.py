"""inspect_embedding over a synthetic index; the query embedding comes from a mock client."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import unittest
import numpy as np
from rag.inspect_embedding import explain
from rag.vectorstore import build_store
from shared.contracts import Chunk


def query_client(vector):
    client = Mock()
    client.embeddings.create.return_value = NS(data=[NS(index=0, embedding=vector)], usage=NS(total_tokens=1))
    return client


class InspectEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'index'
        self.chunks = [Chunk('a', 'alpha', 'doc', 1), Chunk('b', 'beta', 'doc', 2), Chunk('c', 'gamma', 'doc')]
        vectors = np.array([[3, 0], [0, 1], [1, 1]], dtype='float32')
        with patch('rag.vectorstore.embed_texts', return_value=(vectors, 3)):
            build_store(self.chunks, self.folder, 'synthetic-test-only')

    def tearDown(self):
        self.temp.cleanup()

    def test_stored_vectors_are_unit_length_and_dot_products_match_faiss(self):
        query, matches, manifest = explain('question', self.folder, 2, client=query_client([2, 0]))
        self.assertEqual([m.chunk.chunk_id for m in matches], ['a', 'c'])
        np.testing.assert_allclose(query, [1, 0], atol=1e-6)
        np.testing.assert_allclose(matches[0].vector, [1, 0], atol=1e-6)  # [3, 0] was saved normalized.
        for match in matches:
            self.assertAlmostEqual(match.dot_product, match.faiss_score, places=6)
        self.assertEqual(manifest['model'], 'synthetic-test-only')

    def test_empty_question_makes_no_api_call(self):
        client = query_client([1, 0])
        with self.assertRaises(ValueError):
            explain('  ', self.folder, 2, client=client)
        client.embeddings.create.assert_not_called()
