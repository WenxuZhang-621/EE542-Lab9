import importlib
import json
import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from starlette.websockets import WebSocketDisconnect
from webapp.backend.rag_service import ServiceError

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'test-only-secret-with-at-least-thirty-two-characters')
    monkeypatch.setenv('DATABASE_URL', 'sqlite+aiosqlite:///' + str(tmp_path/'web.sqlite'))
    module = importlib.import_module('webapp.backend.app')
    monkeypatch.setattr(module, 'public_access', module.PublicAccess())
    monkeypatch.setattr(module, 'PUBLIC_ORIGIN', '')
    db = create_async_engine(os.environ['DATABASE_URL'])
    monkeypatch.setattr(module, 'engine', db)
    monkeypatch.setattr(module, 'SessionLocal', async_sessionmaker(db, expire_on_commit=False))
    module.active_questions.clear()
    with TestClient(module.app) as value:
        yield value, module

def signup(client, name='alice'):
    result = client.post('/api/signup', json={'username': name, 'password':'test-password-123'})
    assert result.status_code == 200, result.text
    return result.json()

def headers(account):
    return {'Authorization': 'Bearer ' + account['token']}

def body(content, ask_bot=True):
    return {'content': content, 'ask_bot': ask_bot, 'session_id': str(uuid4())}

def test_auth_static_and_history_require_login(client):
    c, app = client
    assert c.get('/').status_code == 200
    assert "script-src 'self'" in c.get('/').headers['content-security-policy']
    assert c.get('/api/messages').status_code == 401
    assert c.get('/api/config').json()['source_count'] == 17
    assert c.get('/manifest.webmanifest').json()['display'] == 'standalone'
    for icon in ('icon-192.png', 'icon-512.png'):
        assert c.get('/assets/'+icon).status_code == 200
    a = signup(c)
    assert c.post('/api/signup', json={'username':'alice','password':'test-password-123'}).status_code == 409
    assert c.post('/api/login', json={'username':'alice','password':'bad-password'}).status_code == 401
    assert c.post('/api/login', json={'username':'alice','password':'test-password-123'}).status_code == 200
    assert c.get('/api/me', headers=headers(a)).json()['username'] == 'alice'
    assert c.post('/api/messages', headers=headers(a), json=body('  ', False)).status_code == 400

def test_two_authenticated_sockets_and_sources_survive_reload(client, monkeypatch):
    c, module = client
    a, b = signup(c), signup(c, 'bob')
    calls = []
    async def answer(question, session_id):
        calls.append((question, session_id))
        return {'answer':'Source-based answer [1]', 'sources':[{'number':1, 'chunk_id':'evidence', 'source':'file.txt', 'page':2, 'title':'Document', 'url':'https://www.irs.gov/', 'excerpt':'Evidence'}]}
    monkeypatch.setattr(module, 'ask_llm', answer)
    with c.websocket_connect('/ws') as wa, c.websocket_connect('/ws') as wb:
        wa.send_json({'token':a['token']}); wb.send_json({'token':b['token']})
        assert wa.receive_json()['type'] == wb.receive_json()['type'] == 'ready'
        response = c.post('/api/messages', headers=headers(a), json=body('CPT\uff1f', False))
        assert response.status_code == 200
        events_a, events_b = [wa.receive_json() for _ in range(4)], [wb.receive_json() for _ in range(4)]
        assert events_a == events_b
        assert [e['type'] for e in events_a] == ['message','bot_status','message','bot_status']
        assert events_a[-1]['status'] == 'done'
    history = c.get('/api/messages', headers=headers(b)).json()
    assert len(history['messages']) == 2
    assert history['messages'][1]['sources'][0]['chunk_id'] == 'evidence'
    assert calls[0][1].startswith(str(a['user_id']) + ':')
    assert history['pending'] == []

def test_failure_and_owner_only_retry(client, monkeypatch):
    c, module = client
    a, b = signup(c), signup(c, 'bob')
    async def unavailable(*args):
        raise ServiceError('llm_unavailable', 'Llama unavailable. Retry.')
    monkeypatch.setattr(module, 'ask_llm', unavailable)
    out = c.post('/api/messages', headers=headers(a), json=body('OPT?')).json()
    assert out['reply']['error_code'] == 'llm_unavailable'
    question_id = out['message']['id']
    retry = {'session_id': str(uuid4())}
    assert c.post(f'/api/messages/{question_id}/retry', headers=headers(b), json=retry).status_code == 404
    async def available(*args):
        return {'answer':'Now available [1]', 'sources':[]}
    monkeypatch.setattr(module, 'ask_llm', available)
    assert c.post(f'/api/messages/{question_id}/retry', headers=headers(a), json=retry).json()['reply']['error_code'] is None

def test_websocket_rejects_unauthenticated_and_cross_origin(client):
    c, module = client
    with pytest.raises(WebSocketDisconnect) as invalid:
        with c.websocket_connect('/ws') as ws:
            ws.send_json({'token':'invalid'})
            ws.receive_json()
    assert invalid.value.code == 4401
    with pytest.raises(WebSocketDisconnect) as origin:
        with c.websocket_connect('/ws', headers={'origin':'https://unrelated.example'}):
            pass
    assert origin.value.code == 4403

def test_normal_chat_does_not_call_model(client, monkeypatch):
    c, module = client
    async def should_not_run(*args):
        raise AssertionError('Ordinary chat must not call the assistant')
    monkeypatch.setattr(module, 'ask_llm', should_not_run)
    a = signup(c)
    out = c.post('/api/messages', headers=headers(a), json=body('Hello everyone', False)).json()
    assert out['reply'] is None

def test_public_signup_invitation_and_login_throttling(client, monkeypatch):
    c, module = client
    code = 'group-test-invitation-12345'
    monkeypatch.setattr(module, 'public_access', module.PublicAccess(True, code))
    credentials = {'username':'invite-user', 'password':'test-password-123'}
    assert c.get('/api/config').json()['registration_requires_code'] is True
    assert code not in c.get('/api/config').text
    for supplied in ('', 'incorrect', 'invalid-invitation-café'):
        assert c.post('/api/signup', json={**credentials, 'registration_code':supplied}).status_code == 403
    assert c.post('/api/login', json=credentials).status_code == 401
    assert c.post('/api/signup', json={**credentials, 'registration_code':code}).status_code == 200
    assert c.post('/api/login', json=credentials).status_code == 200
    for _ in range(4):
        assert c.post('/api/login', json={**credentials, 'password':'wrong-password'}).status_code == 401
    limited = c.post('/api/login', json=credentials)
    assert limited.status_code == 429
    assert int(limited.headers['retry-after']) > 0

def test_public_assistant_limits_before_save_and_on_retry(client, monkeypatch):
    c, module = client
    account = signup(c)
    clock = [0.0]
    access = module.PublicAccess(True, 'group-test-invitation', clock=lambda: clock[0])
    monkeypatch.setattr(module, 'public_access', access)
    calls = []
    async def unavailable(*args):
        calls.append(args)
        raise ServiceError('llm_unavailable', 'Retry later.')
    monkeypatch.setattr(module, 'ask_llm', unavailable)
    first = c.post('/api/messages', headers=headers(account), json=body('Question?')).json()
    question_id = first['message']['id']
    for _ in range(5):
        assert c.post(f'/api/messages/{question_id}/retry', headers=headers(account),
                      json={'session_id':str(uuid4())}).status_code == 200
    history = c.get('/api/messages', headers=headers(account)).json()
    assert c.post('/api/messages', headers=headers(account), json=body('Limited?')).status_code == 429
    assert c.post(f'/api/messages/{question_id}/retry', headers=headers(account),
                  json={'session_id':str(uuid4())}).status_code == 429
    assert c.get('/api/messages', headers=headers(account)).json() == history
    assert len(calls) == 6 and access.active == 0
    clock[0] = 61.0
    assert c.post('/api/messages', headers=headers(account), json=body('Allowed again?')).status_code == 200
    with access.message(account['user_id'], True):
        before = c.get('/api/messages', headers=headers(account)).json()
        assert c.post('/api/messages', headers=headers(account), json=body('Busy?')).status_code == 429
        assert c.get('/api/messages', headers=headers(account)).json() == before
    assert access.active == 0

def test_public_websocket_explicit_origin_behind_proxy(client, monkeypatch):
    c, module = client
    account = signup(c)
    monkeypatch.setattr(module, 'PUBLIC_ORIGIN', 'https://lab.example.com')
    with c.websocket_connect('/ws', headers={'origin':'https://lab.example.com'}) as ws:
        ws.send_json({'token':account['token']})
        assert ws.receive_json()['type'] == 'ready'
