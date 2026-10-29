"""Synthetic-vector unit tests only. No OpenAI API or semantic quality claims."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import unittest
import numpy as np
from rag.embeddings import embed_texts
from rag.vectorstore import build_store, load_store, make_index
from shared.contracts import Chunk


class VectorStoreTests(unittest.TestCase):
    def test_response_order_and_batching(self):
        client = Mock()
        client.embeddings.create.side_effect = [
            NS(data=[NS(index=1, embedding=[0,1]), NS(index=0, embedding=[1,0])], usage=NS(total_tokens=2)),
            NS(data=[NS(index=0, embedding=[1,1])], usage=NS(total_tokens=1))]
        vectors, tokens = embed_texts(['a','b','c'], 'test-model', client=client, batch_size=2)
        np.testing.assert_array_equal(vectors, [[1,0],[0,1],[1,1]])
        self.assertEqual(tokens, 3)
        self.assertEqual(client.embeddings.create.call_count, 2)

    def test_invalid_response_indices(self):
        client = Mock()
        client.embeddings.create.return_value = NS(data=[NS(index=1, embedding=[1,0])], usage=NS(total_tokens=1))
        with self.assertRaises(ValueError):
            embed_texts(['a'], 'test-model', client=client)

    def test_normalized_cosine_ranking(self):
        index = make_index(np.array([[3,0],[0,2],[1,1]]))
        scores, positions = index.search(np.array([[1,0]],dtype='float32'), 3)
        self.assertEqual(positions[0].tolist(), [0,2,1])
        np.testing.assert_allclose(scores[0], [1,2**-.5,0], atol=1e-6)

    def test_store_reload_reuse_and_corruption(self):
        chunks=[Chunk('a','alpha','test',1), Chunk('b','beta','test',2)]
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'index'
            with patch('rag.vectorstore.embed_texts', return_value=(np.array([[1,0],[0,1]],dtype='float32'), 2)) as embed:
                first=build_store(chunks,folder,'synthetic-test-only')
                index, saved, meta=load_store(folder)
                self.assertEqual((index.ntotal,index.d),(2,2))
                self.assertEqual(saved,chunks)
                self.assertEqual(build_store(chunks,folder,'synthetic-test-only')['status'],'unchanged')
                embed.assert_called_once()
                with self.assertRaises(ValueError):
                    build_store(chunks,folder,'different-model')
                (folder/'chunks.jsonl').write_text('corrupt')
                with self.assertRaises(ValueError): load_store(folder)

    def test_failure_does_not_publish_index(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'index'
            with patch('rag.vectorstore.embed_texts', side_effect=RuntimeError('simulated API failure')):
                with self.assertRaises(RuntimeError):
                    build_store([Chunk('a','text','test')],folder,'test-model')
            self.assertFalse(folder.exists())

    def test_zero_vectors_rejected(self):
        with self.assertRaises(ValueError): make_index(np.zeros((1,2)))
