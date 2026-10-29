"""Retrieval over a synthetic index; the query embedding comes from a mock client."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import unittest
import numpy as np
from rag.retrieval import VectorStore
from rag.vectorstore import build_store
from shared.contracts import Chunk


def query_client(vector):
    client = Mock()
    client.embeddings.create.return_value = NS(data=[NS(index=0, embedding=vector)], usage=NS(total_tokens=1))
    return client


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'index'
        self.chunks = [Chunk('a', 'alpha', 'doc', 1), Chunk('b', 'beta', 'doc', 2), Chunk('c', 'gamma', 'doc')]
        vectors = np.array([[1, 0], [0, 1], [1, 1]], dtype='float32')
        with patch('rag.vectorstore.embed_texts', return_value=(vectors, 3)):
            build_store(self.chunks, self.folder, 'synthetic-test-only')

    def tearDown(self):
        self.temp.cleanup()

    def test_ranked_hits_map_back_to_chunks(self):
        client = query_client([2, 0])
        hits = VectorStore(self.folder, client=client).search('question', 2)
        self.assertEqual([hit.chunk for hit in hits], [self.chunks[0], self.chunks[2]])
        np.testing.assert_allclose([hit.score for hit in hits], [1, 2 ** -.5], atol=1e-6)
        # The query must use the model recorded with the index.
        self.assertEqual(client.embeddings.create.call_args.kwargs['model'], 'synthetic-test-only')

    def test_k_larger_than_index(self):
        hits = VectorStore(self.folder, client=query_client([0, 1])).search('question', 10)
        self.assertEqual(len(hits), 3)
        self.assertEqual(hits[0].chunk.chunk_id, 'b')

    def test_rejects_empty_question_bad_k_and_dimension(self):
        client = query_client([1, 0, 0])
        store = VectorStore(self.folder, client=client)
        with self.assertRaises(ValueError):
            store.search('  ', 2)
        with self.assertRaises(ValueError):
            store.search('question', 0)
        client.embeddings.create.assert_not_called()
        with self.assertRaises(ValueError):
            store.search('question', 2)
