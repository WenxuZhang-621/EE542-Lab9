"""Part 4 topic data: download the official sources in data/topic/sources.json, then curate
the corpus folder that the knowledge base is built from.

  python -m rag.topic_data fetch     # downloads -> data/raw/topic/downloads, record -> sources.lock.json
  python -m rag.topic_data curate    # corpus    -> data/raw/topic/corpus
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import urllib.request

from rag.documents import extract_pages
from shared.config import ROOT

SOURCES = ROOT / 'data/topic/sources.json'
LOCK = ROOT / 'data/topic/sources.lock.json'
CATALOG = ROOT / 'data/topic/catalog.json'
DOWNLOADS = ROOT / 'data/raw/topic/downloads'
CORPUS = ROOT / 'data/raw/topic/corpus'
# Some government sites reject non-browser clients; this only fetches public documents.
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
SIGNATURES = {'.pdf': b'%PDF', '.xml': b'<?xml', '.html': b'<!DOCTYPE html'}


def check_type(name: str, content: bytes) -> None:
    # Sites answer missing files with an HTML error page and status 200; never save that as data.
    signature = SIGNATURES.get(Path(name).suffix.lower())
    if signature and not content.lstrip()[:len(signature)].lower() == signature.lower():
        raise ValueError(f'{name}: downloaded content is not a {Path(name).suffix} file.')


def load_sources() -> list[dict]:
    return json.loads(SOURCES.read_text(encoding='utf-8'))['sources']


def fetch(sources: list[dict], folder: Path, force: bool = False) -> list[dict]:
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sources:
        path = folder / source['file']
        if force or not path.exists():
            # eCFR's API refuses uncompressed responses, so ask for gzip and unpack it here.
            request = urllib.request.Request(source['url'], headers={
                'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip'})
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read()
                if response.headers.get('Content-Encoding') == 'gzip':
                    content = gzip.decompress(content)
            check_type(source['file'], content)
            partial = path.with_suffix(path.suffix + '.part')
            partial.write_bytes(content)
            partial.rename(path)  # A failed download never leaves a half file under the real name.
        content = path.read_bytes()
        records.append({'id': source['id'], 'file': source['file'], 'url': source['url'],
                        'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                        'fetched_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
        print(f"{source['file']}: {len(content):,} bytes")
    return records


def ecfr_paragraph(xml: str, start: str, end: str) -> str:
    """Plain text of one top-level paragraph of an eCFR section, e.g. (f) up to (g)."""
    begin = xml.index(f'<P>({start}) ')
    fragment = xml[begin:xml.index(f'<P>({end}) ', begin)]
    fragment = re.sub(r'</TD>\s*<TD[^>]*>', ' | ', fragment)
    fragment = re.sub(r'</(P|TR|CAPTION|DIV|HD)>', '\n', fragment)
    text = html.unescape(re.sub(r'<[^>]+>', '', fragment))
    lines = (' '.join(line.split()) for line in text.splitlines())
    return '\n'.join(line for line in lines if line and not re.fullmatch(r'\(\w+\) \[Reserved\]', line))


def clean_irs_pdf(content: bytes) -> str:
    """IRS PDF pages as form-feed separated text, without proof headers or extraction artifacts."""
    pages = []
    for page in extract_pages('irs.pdf', content):
        # Every page of the posted PDF starts with a print-shop proof header ending at this sentence.
        text = re.sub(r'\A.*?MUST be removed before printing\.\s*', '', page.text, flags=re.S)
        text = re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)  # "territo-\nrial" -> "territorial"
        text = re.sub(r'\b([TYVW]) (?=[a-z])', r'\1', text)  # kerning gaps: "Y ou", "T ax" -> "You", "Tax"
        pages.append(re.sub(r'(\w) -(?=\w)', r'\1-', text))  # "Form W -4", "self -employment"
    return '\f'.join(pages)


def curate(sources: list[dict], downloads: Path, corpus: Path) -> list[dict]:
    """Copy each source into the corpus. 8 CFR 214.2 keeps only paragraph (f), the F-1 rules;
    IRS PDFs become cleaned text with one form feed per page."""
    corpus.mkdir(parents=True, exist_ok=True)
    entries = []
    for source in sources:
        original = downloads / source['file']
        if source.get('curate') == 'cfr-214.2(f)':
            target = corpus / f"{source['id']}.txt"
            body = ecfr_paragraph(original.read_text(encoding='utf-8'), 'f', 'g')
            target.write_text(f"{source['title']}\n{body}\n", encoding='utf-8')
        elif source.get('curate') == 'irs-pdf':
            target = corpus / f"{source['id']}.txt"
            target.write_text(clean_irs_pdf(original.read_bytes()), encoding='utf-8')
        else:
            target = corpus / source['file']
            shutil.copyfile(original, target)
        entries.append({'source': target.name, **{k: source[k] for k in ('id', 'publisher', 'title', 'url')}})
        print(f'{target.name}: {target.stat().st_size:,} bytes')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['fetch', 'curate'])
    parser.add_argument('--force', action='store_true', help='Download again even if the file exists.')
    args = parser.parse_args()
    sources = load_sources()
    if args.command == 'fetch':
        records = fetch(sources, DOWNLOADS, args.force)
        LOCK.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    else:
        # Chunk "source" values are corpus file names; this maps them to titles and URLs for A.
        entries = curate(sources, DOWNLOADS, CORPUS)
        CATALOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
