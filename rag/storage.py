"""Store immutable document versions and extracted pages in MySQL."""
import hashlib
import os
from datetime import datetime, timezone
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, MetaData, String,
                        Table, Text, create_engine, select)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.dialects.mysql import LONGTEXT
from dotenv import load_dotenv
from rag.documents import DocumentPage
from shared.config import ROOT

metadata = MetaData()
documents = Table(
    'rag_documents', metadata,
    Column('document_id', String(64), primary_key=True),
    Column('source', Text, nullable=False),
    Column('content_sha256', String(64), nullable=False),
    Column('page_count', Integer, nullable=False),
    Column('created_at', DateTime, nullable=False),
    mysql_charset='utf8mb4', mysql_engine='InnoDB',
)
pages = Table(
    'rag_document_pages', metadata,
    Column('document_id', String(64), ForeignKey('rag_documents.document_id'), primary_key=True),
    Column('ordinal', Integer, primary_key=True),
    Column('page_number', Integer, nullable=True),
    Column('text', Text().with_variant(LONGTEXT(), 'mysql'), nullable=False),
    mysql_charset='utf8mb4', mysql_engine='InnoDB',
)


def get_engine() -> Engine:
    load_dotenv(ROOT / '.env')
    value = os.getenv('DATABASE_URL')
    if not value:
        raise ValueError('Set DATABASE_URL in repository-root .env.')
    url = make_url(value)
    if url.get_backend_name() != 'mysql':
        raise ValueError('This lab importer requires MySQL.')
    # A uses asyncmy; this synchronous batch job uses PyMySQL against the same DB.
    url = url.set(drivername='mysql+pymysql')
    return create_engine(url, pool_pre_ping=True,
                         connect_args={'charset': 'utf8mb4', 'connect_timeout': 10})


def init_schema(engine: Engine) -> None:
    metadata.create_all(engine)


def save_document(engine: Engine, source: str, content: bytes,
                  extracted: list[DocumentPage]) -> dict:
    if not extracted or not any(p.text.strip() for p in extracted):
        raise ValueError('No extractable text; OCR may be needed. Nothing was stored.')
    digest = hashlib.sha256(content).hexdigest()
    document_id = hashlib.sha256((source + '\0' + digest).encode()).hexdigest()
    # A single document and all its pages commit together or roll back together.
    with engine.begin() as connection:
        existing = connection.execute(select(documents.c.document_id).where(
            documents.c.document_id == document_id)).scalar_one_or_none()
        if existing:
            status = 'skipped'
        else:
            connection.execute(documents.insert().values(
                document_id=document_id, source=source, content_sha256=digest,
                page_count=len(extracted), created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
            connection.execute(pages.insert(), [
                {'document_id': document_id, 'ordinal': i, 'page_number': page.page, 'text': page.text}
                for i, page in enumerate(extracted, start=1)
            ])
            status = 'inserted'
    return {'source': source, 'document_id': document_id, 'sha256': digest,
            'pages': len(extracted), 'characters': sum(len(p.text) for p in extracted),
            'empty_pages': sum(not p.text.strip() for p in extracted), 'status': status}
