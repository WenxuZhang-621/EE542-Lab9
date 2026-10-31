"""Exercise a running local website with two real HTTP/WebSocket clients.

Creates uniquely named QA accounts/messages in the selected local database.
Does not invoke the LLM or send API keys; never targets a remote server.
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
        raise ValueError('This smoke test only accepts a local server')
    accounts = []
    async with httpx.AsyncClient(base_url=base, timeout=15) as client:
        for suffix in ('a','b'):
            credentials = {'username':f'qa-{uuid4().hex[:12]}-{suffix}', 'password':secrets.token_urlsafe(24)}
            response = await client.post('/api/signup', json={**credentials,
                'registration_code':dotenv_values(ROOT/'.env').get('REGISTRATION_CODE', '')}); response.raise_for_status()
            login = await client.post('/api/login', json=credentials); login.raise_for_status()
            accounts.append(login.json())
        socket_url = ('wss' if url.scheme == 'https' else 'ws')+'://'+url.netloc+'/ws'
        async with websockets.connect(socket_url, origin=base) as a, websockets.connect(socket_url, origin=base) as b:
            for socket, account in zip((a,b), accounts):
                await socket.send(json.dumps({'token':account['token']}))
                assert json.loads(await asyncio.wait_for(socket.recv(),5))['type'] == 'ready'
            for account in accounts:
                payload = {'content':'Local automated QA: shared message round-trip.', 'ask_bot':False, 'session_id':str(uuid4())}
                response = await client.post('/api/messages', json=payload, headers={'Authorization':'Bearer '+account['token']})
                response.raise_for_status(); saved = response.json()['message']
                received = [json.loads(await asyncio.wait_for(socket.recv(),5)) for socket in (a,b)]
                assert all(e['message']['id'] == saved['id'] for e in received)
                history = await client.get('/api/messages', headers={'Authorization':'Bearer '+account['token']})
                assert any(m['id'] == saved['id'] for m in history.json()['messages'])
        health = (await client.get('/api/health')).json()
    print(json.dumps({'registration_and_login':True, 'two_way_websocket_broadcast':True,
                      'database_history_readback':True, 'database':health['database'],
                      'llm_invoked':False}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    asyncio.run(run(parser.parse_args().base_url.rstrip('/')))
