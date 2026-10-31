"""Explicit live test: two OpenAI embeddings and real local Llama answers.

Creates a QA account and two messages in the local website's database.
No credentials are printed; requires services and a locally configured API key.
"""
import argparse
import asyncio
import json
import secrets
from urllib.parse import urlparse
from uuid import uuid4
import httpx
import websockets
from dotenv import dotenv_values
from shared.config import ROOT

async def run(base):
    url = urlparse(base)
    if url.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('This test only accepts a local server')
    credentials = {'username': 'live-qa-'+uuid4().hex[:10], 'password':secrets.token_urlsafe(24)}
    results = []
    session_id = str(uuid4())
    async with httpx.AsyncClient(base_url=base, timeout=240) as client:
        response = await client.post('/api/signup', json={**credentials,
            'registration_code':dotenv_values(ROOT/'.env').get('REGISTRATION_CODE', '')})
        response.raise_for_status()
        response = await client.post('/api/login', json=credentials)
        response.raise_for_status()
        token = response.json()['token']
        headers = {'Authorization':'Bearer '+token}
        socket_url = ('wss' if url.scheme == 'https' else 'ws')+'://'+url.netloc+'/ws'
        async with websockets.connect(socket_url, origin=base) as socket:
            await socket.send(json.dumps({'token':token}))
            assert json.loads(await asyncio.wait_for(socket.recv(),10))['type'] == 'ready'
            for question in ('What is Form 8843 used for?', 'What information does that form ask students to provide?'):
                response = await client.post('/api/messages', headers=headers,
                    json={'content':question, 'ask_bot':True, 'session_id':session_id})
                response.raise_for_status()
                saved = response.json()
                reply = saved['reply']
                assert reply and not reply.get('error_code'), (reply or {}).get('error_code', 'missing_reply')
                assert reply['sources'] and not reply.get('citation_warning'), 'missing_cited_sources'
                # A fluent, cited answer can still lose the follow-up's subject.
                assert '8843' in reply['content'], 'followup_lost_form_reference'
                assert any(s['source'] == 'irs-f8843.txt' for s in reply['sources']), 'wrong_form_retrieved'
                if not results:
                    assert 'substantial presence' in reply['content'].lower(), 'missing_form_purpose'
                else:
                    assert any(term in reply['content'].lower() for term in ('academic institution', 'school')), 'missing_student_form_fields'
                    assert 'parts i and ii' not in reply['content'].lower(), 'teacher_section_used_for_student'
                events = []
                while True:
                    event = json.loads(await asyncio.wait_for(socket.recv(),10))
                    events.append(event)
                    if event.get('type') == 'bot_status' and event.get('question_id') == saved['message']['id'] and event.get('status') == 'done':
                        break
                assert any(e.get('status') == 'thinking' for e in events), 'missing_loading_event'
                assert any(e.get('message',{}).get('id') == reply['id'] for e in events), 'missing_reply_broadcast'
                history = await client.get('/api/messages', headers=headers)
                history.raise_for_status()
                restored = next(m for m in history.json()['messages'] if m['id'] == reply['id'])
                assert restored['sources'] == reply['sources'], 'sources_not_persisted'
                results.append({'question':question, 'answer':reply['content'], 'sources':reply['sources'],
                    'reply_id':reply['id'], 'loading_and_reply_broadcast':True, 'sources_persisted':True})
    print(json.dumps({'real_services':True, 'backend':'MySQL + local llama.cpp + OpenAI embeddings',
        'two_turn_conversation':results}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    asyncio.run(run(parser.parse_args().base_url.rstrip('/')))
