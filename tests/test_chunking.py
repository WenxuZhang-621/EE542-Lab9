import tempfile
from pathlib import Path
import unittest
from rag.chunking import split_page, write_once_or_verify


class ChunkingTests(unittest.TestCase):
    def test_long_line_bounded_and_overlap(self):
        text = ''.join(chr(0x4e00 + i) for i in range(1200))
        parts = split_page(text, 500, 100, '\n')
        self.assertEqual([len(p) for p in parts], [500, 500, 400])
        self.assertEqual(parts[0][-100:], parts[1][:100])
        self.assertEqual(parts[0] + parts[1][100:] + parts[2][100:], text)

    def test_newlines_preserved_and_empty_ignored(self):
        text = 'First line\nSecond line\n第三行\n'
        self.assertEqual(split_page(text, 500, 100, '\n'), [text])
        self.assertEqual(split_page(' \n\t', 500, 100, '\n'), [])

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            split_page('abc', 500, 500, '\n')

    def test_export_protects_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'chunks.jsonl'
            self.assertEqual(write_once_or_verify(path, 'one'), 'created')
            self.assertEqual(write_once_or_verify(path, 'one'), 'unchanged')
            with self.assertRaises(ValueError):
                write_once_or_verify(path, 'two')
            self.assertEqual(path.read_text(), 'one')
