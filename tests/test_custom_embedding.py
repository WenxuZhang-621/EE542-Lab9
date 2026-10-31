"""Checks for B's custom embedding: the clustering, the histogram and the handoff API."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_embedding.kmeans import assign, kmeans, pairwise_sq_dist, soft_assign  # noqa: E402
from custom_embedding.model import HistogramConfig, HistogramEmbedder  # noqa: E402
from custom_embedding.tokenize import tokenize  # noqa: E402

TEXTS = [
    "An F-1 student must maintain a full course of study each term to keep status.",
    "Optional practical training allows F-1 students to work after completing the program.",
    "Curricular practical training is work authorization that is part of the curriculum.",
    "Nonresident aliens file Form 1040-NR to report wages and request a refund of tax withheld.",
    "The Social Security number is required for employment and is issued by the SSA.",
    "A student may transfer to another SEVP-certified school by asking the DSO to release the record.",
] * 5  # repeat so every word reaches min_count


class TestTokenize(unittest.TestCase):
    def test_lowercase_and_digits(self):
        self.assertEqual(tokenize("Form 1040-NR, F-1!"), ["form", "1040-nr", "f-1"])

    def test_stopwords(self):
        self.assertEqual(tokenize("the student and the DSO", drop_stopwords=True), ["student", "dso"])


class TestKMeans(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.x = np.concatenate([rng.normal(c, 0.2, (40, 5)) for c in (-3, 0, 3)]).astype(np.float32)

    def test_pairwise_matches_numpy(self):
        c = self.x[:4]
        ref = ((self.x[:, None, :] - c[None, :, :]) ** 2).sum(-1)
        np.testing.assert_allclose(pairwise_sq_dist(self.x, c), ref, atol=1e-3)

    def test_finds_three_well_separated_clusters(self):
        r = kmeans(self.x, 3, seed=1)
        self.assertEqual(r.centroids.shape, (3, 5))
        groups = [set(r.labels[i * 40:(i + 1) * 40]) for i in range(3)]
        self.assertTrue(all(len(g) == 1 for g in groups), groups)
        self.assertEqual(len(set.union(*groups)), 3)
        self.assertTrue(r.inertia < 0.2 * 120 * 5)

    def test_inertia_never_increases(self):
        prev = np.inf
        for it in (1, 2, 3, 10):
            r = kmeans(self.x, 3, max_iter=it, tol=0.0, seed=2)
            self.assertLessEqual(r.inertia, prev + 1e-4)
            prev = r.inertia

    def test_cosine_centroids_are_unit(self):
        r = kmeans(self.x, 3, metric="cosine", seed=3)
        np.testing.assert_allclose(np.linalg.norm(r.centroids, axis=1), 1.0, atol=1e-5)

    def test_assign_and_soft_assign(self):
        r = kmeans(self.x, 3, seed=4)
        np.testing.assert_array_equal(assign(self.x, r.centroids), r.labels)
        idx, w = soft_assign(self.x, r.centroids, "euclidean", 2, 0.5)
        self.assertEqual(idx.shape, (120, 2))
        np.testing.assert_allclose(w.sum(axis=1), 1.0, atol=1e-6)


class TestHistogram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = HistogramEmbedder(HistogramConfig(n=20, k=8, min_count=1, epochs=5)).fit(TEXTS)

    def test_baseline_histogram_sums_to_known_fraction(self):
        text = TEXTS[0]
        v = self.model.embed(text)
        self.assertEqual(v.shape, (8,))
        toks = tokenize(text)
        known = sum(t in self.model.vocab for t in toks)
        self.assertAlmostEqual(float(v.sum()), known / len(toks), places=5)  # divided by total words
        self.assertTrue((v >= 0).all())

    def test_unknown_only_text_is_zero_vector(self):
        self.assertEqual(float(np.abs(self.model.embed("zzzz qqqq")).sum()), 0.0)

    def test_same_model_for_documents_and_queries(self):
        a = self.model.embed("practical training")
        b = self.model.embed("practical training")
        np.testing.assert_array_equal(a, b)

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            self.model.save(Path(d))
            again = HistogramEmbedder.load(Path(d))
            np.testing.assert_array_equal(again.embed(TEXTS[3]), self.model.embed(TEXTS[3]))

    def test_variants_have_expected_shapes(self):
        m = HistogramEmbedder(HistogramConfig(n=20, k=8, min_count=1, epochs=5, metric="cosine", weighting="idf",
                                              soft_top_m=3, normalize="l2", append_mean_vector=0.5)).fit(TEXTS)
        v = m.embed(TEXTS[1])
        self.assertEqual(v.shape, (28,))
        self.assertAlmostEqual(float(np.linalg.norm(v[:8])), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
