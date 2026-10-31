import asyncio
import json
import threading
import time
import httpx
import pytest
from shared.contracts import Chunk, SearchHit
from webapp.backend.rag_service import RAGService, ServiceError, expand_context, context_chunks, include_named_sections

HIT = SearchHit(Chunk('chunk-1', 'Students must keep the required records.', 'irs-f8843.txt', 1), .8)


@pytest.mark.asyncio
async def test_cut_sentence_continuation_reaches_model_and_saved_sources():
    chunks = context_chunks()
    cut = next(c for c in chunks if c.source == 'irs-f8843.txt' and c.text.endswith('explain the basis '))
    hits = expand_context([SearchHit(cut, .8)], chunks)
    async def respond(request):
        prompt = json.loads(request.content)['messages'][1]['content']
        assert 'exclude days of presence' in prompt
        assert 'substantial presence test' in prompt
        return httpx.Response(200, json={'choices':[{'message':{'content':'Explains excluded days for the substantial presence test. [1]'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await RAGService(lambda *args: hits, client).answer('What is Form 8843 used for?', 'cut-sentence')
    source = result['sources'][0]
    assert source['chunk_id'] == cut.chunk_id and source['page'] == 3
    assert len(source['context_chunk_ids']) == 2
    assert 'exclude days of presence' in source['excerpt']


def test_context_expansion_does_not_cross_source_or_page_boundaries():
    chunks = [Chunk('other', 'Unrelated document', 'other.txt', 2),
              Chunk('hit', 'Start', 'source.txt', 2),
              Chunk('next', 'Continuation', 'source.txt', 2),
              Chunk('page', 'Different page', 'source.txt', 3)]
    expanded = expand_context([SearchHit(chunks[1], .9), SearchHit(chunks[2], .8)], chunks)
    assert [c.chunk_id for c in expanded[0].context] == ['hit', 'next']
    assert [c.chunk_id for c in expanded[1].context] == ['hit', 'next']
    assert [h.chunk.chunk_id for h in expanded] == ['hit', 'next']


def test_named_form_student_section_is_not_displaced_by_teacher_section():
    chunks = context_chunks()
    teacher = next(c for c in chunks if c.source == 'irs-f8843.txt' and c.text.startswith('Form 8843 (2025) Page 4'))
    hits = [SearchHit(teacher, .8)]
    catalog = {'irs-f8843.txt': {'title': 'Form 8843, Statement for Exempt Individuals'}}
    result = include_named_sections('What information does Form 8843 ask students to provide?', hits, chunks, catalog, 4)
    assert '9 Enter the name, address' in result[0].chunk.text
    assert 'Part III—Students' in result[1].chunk.text
    assert result[-1].chunk == teacher
    assert len(result) <= 4
    assert include_named_sections('What information does Form I-20 ask students to provide?', hits, chunks, catalog, 4) == hits

@pytest.mark.asyncio
async def test_context_sources_followup_and_isolation():
    queries, requests, threads = [], [], []
    main_thread = threading.get_ident()
    def retrieve(q, k):
        queries.append(q); threads.append(threading.get_ident())
        return [HIT]
    async def respond(request):
        body = json.loads(request.content); requests.append(body)
        text = 'Which records must the student keep?' if 'Rewrite this follow-up' in body['messages'][0]['content'] else 'Keep the records described in the document. [1]'
        return httpx.Response(200, json={'choices': [{'message': {'content': text}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        service = RAGService(retrieve, client)
        first = await service.answer('Which records?', 'user1:session1')
        await service.answer('And for me?', 'user1:session1')
        await service.answer('New user question', 'user2:session1')
    assert all(t != main_thread for t in threads)
    assert queries == ['Which records?', 'Which records must the student keep?', 'New user question']
    assert first['sources'][0]['url'].startswith('https://www.irs.gov/')
    assert first['sources'][0]['page'] == 1 and first['sources'][0]['cited']
    assert 'Students must keep' in requests[0]['messages'][1]['content']
    assert requests[1]['messages'][-1] == {'role': 'user', 'content': 'And for me?'}
    assert requests[1]['messages'][1]['content'] == 'Which records?'
    assert 'Which records?' not in requests[-1]['messages'][1]['content']
    assert len(service.sessions['user1:session1'].turns) == 4

@pytest.mark.asyncio
async def test_slow_retrieval_does_not_block_loop():
    def slow(*args):
        time.sleep(.1); return []
    service = RAGService(slow)
    task = asyncio.create_task(service.answer('Question', 'session'))
    await asyncio.sleep(.02)
    assert not task.done()
    result = await task
    assert result['sources'] == []

@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['retrieval', 'http', 'invalid_citation', 'empty'])
async def test_failure_is_safe_and_does_not_change_memory(case):
    def retrieve(*args):
        if case == 'retrieval': raise RuntimeError('secret-api-key')
        return [HIT]
    async def respond(request):
        if case == 'http': return httpx.Response(503, text='secret-api-key')
        return httpx.Response(200, json={'choices':[{'message':{'content': 'Wrong citation [9]' if case == 'invalid_citation' else ''}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        service = RAGService(retrieve, client)
        with pytest.raises(ServiceError) as error:
            await service.answer('Question?', 'session')
        assert 'secret-api-key' not in str(error.value)
        assert service.sessions['session'].turns == []

@pytest.mark.asyncio
@pytest.mark.parametrize('code', ['credit_balance_exhausted', 'insufficient_quota'])
async def test_embedding_credit_failure_preserves_memory_and_hides_upstream_details(code):
    class QuotaError(Exception):
        pass
    def retrieve(*args):
        error = QuotaError('private upstream detail')
        error.code = code
        raise error
    service = RAGService(retrieve)
    with pytest.raises(ServiceError) as error:
        await service.answer('Question?', 'quota-session')
    assert error.value.code == 'embedding_credit_exhausted'
    assert 'API credits' in str(error.value)
    assert 'private upstream detail' not in str(error.value)
    assert service.sessions['quota-session'].turns == []

@pytest.mark.asyncio
async def test_same_session_calls_are_serialized():
    active = 0
    async def respond(request):
        nonlocal active
        active += 1
        assert active == 1
        await asyncio.sleep(.01)
        active -= 1
        return httpx.Response(200, json={'choices':[{'message':{'content':'Supported [1]'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        service = RAGService(lambda *a: [HIT], client)
        await asyncio.gather(service.answer('First?', 'one'), service.answer('Second?', 'one'))
        assert len(service.sessions['one'].turns) == 4
