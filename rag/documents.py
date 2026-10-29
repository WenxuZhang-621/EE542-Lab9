"""Extract source text before chunking. No database or model calls here."""
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_BYTES = 20 * 1024 * 1024
SUPPORTED_SUFFIXES = {'.pdf', '.txt', '.md', '.html', '.htm'}


@dataclass(frozen=True)
class DocumentPage:
    source: str
    page: int | None
    text: str


class _ArticleText(HTMLParser):
    """Collect readable text from a web page's main article, without menus or scripts."""
    SKIP = {'script', 'style', 'noscript', 'svg', 'nav', 'header', 'footer', 'aside', 'form',
            'button', 'template', 'select'}
    BLOCK = {'p', 'div', 'section', 'article', 'main', 'br', 'li', 'tr', 'table', 'ul', 'ol',
             'dd', 'dt', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    VOID = {'br', 'img', 'hr', 'meta', 'link', 'input', 'source', 'wbr'}

    def __init__(self, container: str):
        super().__init__(convert_charrefs=True)
        self.container, self.inside, self.skipping = container, 0, 0
        self.title, self.in_title, self.parts = '', False, []

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        if tag == self.container:
            self.inside += 1
        if tag in self.SKIP and tag not in self.VOID:
            self.skipping += 1
        if tag in self.BLOCK:
            self.parts.append('\n- ' if tag == 'li' else '\n')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == self.container and self.inside:
            self.inside -= 1
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1
        if tag in self.BLOCK:
            self.parts.append('\n')

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.inside and not self.skipping:
            # Keep edge spaces: "You <b>must</b> have" arrives as three pieces.
            text = ' '.join(data.split())
            self.parts.append((' ' if data[:1].isspace() else '') + text
                              + (' ' if text and data[-1:].isspace() else ''))


def html_to_text(html: str) -> str:
    lowered = html.lower()
    container = next((tag for tag in ('article', 'main') if f'<{tag}' in lowered), 'body')
    parser = _ArticleText(container)
    parser.feed(html)
    parser.close()
    lines = [' '.join(line.split()) for line in ''.join(parser.parts).splitlines()]
    body = '\n'.join(line for line in lines if line and line != '-')
    # The page title names the topic, which helps chunks that start mid-article.
    title = ' '.join(parser.title.split()).split(' | ')[0]
    return f'{title}\n{body}' if title and not body.startswith(title) else body


def extract_pages(filename: str, content: bytes) -> list[DocumentPage]:
    """Return source pages, including empty PDF pages so missing text is visible."""
    source = Path(filename).name
    suffix = Path(source).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError('Supported formats: PDF, UTF-8 TXT, Markdown and HTML.')
    if not content:
        raise ValueError('The file is empty.')
    if len(content) > MAX_BYTES:
        raise ValueError('Each file must be at most 20 MiB.')
    if suffix != '.pdf':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Save the text file using UTF-8 encoding.') from exc
        if suffix in {'.html', '.htm'}:
            text = html_to_text(text)
        if '\f' in text:
            # Form feeds separate pages (as in pdftotext output), so cleaned PDFs keep page numbers.
            return [DocumentPage(source=source, page=i, text=page)
                    for i, page in enumerate(text.split('\f'), start=1)]
        return [DocumentPage(source=source, page=None, text=text)]

    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ValueError('Upload an unencrypted PDF.')
        return [
            DocumentPage(source=source, page=i, text=page.extract_text() or '')
            for i, page in enumerate(reader.pages, start=1)
        ]
    except PdfReadError as exc:
        raise ValueError('The PDF could not be read. Check that it is a valid PDF.') from exc
