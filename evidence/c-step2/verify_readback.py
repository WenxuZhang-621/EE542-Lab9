from pathlib import Path
import json
from sqlalchemy import select, text
from rag.documents import extract_pages
from rag.storage import get_engine, documents, pages
engine=get_engine()
with engine.connect() as conn:
 print('MySQL version:', conn.execute(text('SELECT VERSION()')).scalar_one())
 rows=conn.execute(select(documents)).mappings().all()
 for row in rows:
  path=Path('data/raw/part3-demo')/row['source']
  if not path.exists(): continue
  original=extract_pages(path.name,path.read_bytes())
  saved=conn.execute(select(pages.c.page_number,pages.c.text).where(pages.c.document_id==row['document_id']).order_by(pages.c.ordinal)).all()
  assert saved==[(p.page,p.text) for p in original]
  print(json.dumps({'source':row['source'],'pages':len(saved),'characters':sum(len(p.text) for p in original),'every_page_exact_match':True},ensure_ascii=False))
engine.dispose()
