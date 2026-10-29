import unittest
from io import BytesIO
from pypdf import PdfWriter
from rag.documents import extract_pages, MAX_BYTES


class ExtractionTests(unittest.TestCase):
    def test_utf8_text_and_source(self):
        page = extract_pages('../notes.md', '中文 RAG'.encode())[0]
        self.assertEqual((page.source, page.page, page.text), ('notes.md', None, '中文 RAG'))

    def test_blank_pdf_preserves_page(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        output = BytesIO()
        writer.write(output)
        page = extract_pages('blank.pdf', output.getvalue())[0]
        self.assertEqual((page.page, page.text), (1, ''))

    def test_invalid_inputs(self):
        for name, data in [('a.txt', b''), ('a.txt', b'\xff'), ('a.exe', b'abc'),
                           ('a.pdf', b'not a pdf'), ('big.txt', b'a' * (MAX_BYTES + 1))]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                extract_pages(name, data)

    def test_html_keeps_article_text_only(self):
        html = ('<html><head><title>OPT | Study in the States</title><script>var x;</script></head><body>'
                '<nav>Menu</nav><article><h1>OPT</h1><p>You <b>must</b> have an <a href="#">EAD</a>.</p>'
                '<ul><li>First</li><li>Second</li></ul></article><footer>Footer</footer></body></html>')
        page = extract_pages('opt.html', html.encode())[0]
        self.assertEqual((page.page, page.text), (None, 'OPT\nYou must have an EAD.\n- First\n- Second'))

    def test_html_title_added_when_article_lacks_it(self):
        html = '<title>Maintaining Status | DHS</title><main><p>Keep your I-20 valid.</p></main>'
        self.assertEqual(extract_pages('a.htm', html.encode())[0].text,
                         'Maintaining Status\nKeep your I-20 valid.')

    def test_form_feeds_become_numbered_pages(self):
        pages = extract_pages('p519.txt', 'one\fpage two\f'.encode())
        self.assertEqual([(p.page, p.text) for p in pages], [(1, 'one'), (2, 'page two'), (3, '')])

    def test_encrypted_pdf(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt('password')
        output = BytesIO()
        writer.write(output)
        with self.assertRaisesRegex(ValueError, 'unencrypted'):
            extract_pages('locked.pdf', output.getvalue())


if __name__ == '__main__':
    unittest.main()
