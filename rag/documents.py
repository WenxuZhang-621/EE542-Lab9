"""Extract source text before chunking. No database or model calls here."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_BYTES = 20 * 1024 * 1024
SUPPORTED_SUFFIXES = {'.pdf', '.txt', '.md'}


@dataclass(frozen=True)
class DocumentPage:
    source: str
    page: int | None
    text: str


def extract_pages(filename: str, content: bytes) -> list[DocumentPage]:
    """Return source pages, including empty PDF pages so missing text is visible."""
    source = Path(filename).name
    suffix = Path(source).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError('Supported formats: PDF, UTF-8 TXT and Markdown.')
    if not content:
        raise ValueError('The file is empty.')
    if len(content) > MAX_BYTES:
        raise ValueError('Each file must be at most 20 MiB.')
    if suffix != '.pdf':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Save the text file using UTF-8 encoding.') from exc
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
