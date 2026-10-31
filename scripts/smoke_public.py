"""Verify only the HTTPS website explicitly configured in local PUBLIC_ORIGIN.

Creates two temporary QA accounts/messages and makes two real RAG requests.
Uses public DNS-over-HTTPS to avoid this PC's Tailscale split DNS. TLS hostname
and certificate verification remain enabled. No credentials enter the report.
"""
import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import secrets
import socket
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import dotenv_values
import httpx
import websockets
from shared.config import ROOT


@contextmanager
def public_dns(host, ip):
    original = socket.getaddrinfo
    def resolve(name, port, *args, **kwargs):
        normalized = name.decode() if isinstance(name, bytes) else name
        return original(ip if normalized == host else name, port, *args, **kwargs)
    socket.getaddrinfo = resolve
    try:
        yield
    finally:
        socket.getaddrinfo = original


async def run(base):
    config = dotenv_values(ROOT/'.env')
    if base != (config.get('PUBLIC_ORIGIN') or '').rstrip('/'):
        raise ValueError('The URL must exactly match PUBLIC_ORIGIN in local .env.')
    parsed = urlparse(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.username or parsed.port:
        raise ValueError('PUBLIC_ORIGIN must be a bare HTTPS origin on port 443.')
    async with httpx.AsyncClient(timeout=30, trust_env=False) as dns:
        response = await dns.get('https://dns.google/resolve', params={'name':parsed.hostname, 'type':'A'})
        response.raise_for_status()
        addresses = [a['data'] for a in response.json().get('Answer', [])
                     if a['type'] == 1 and ipaddress.ip_address(a['data']).is_global]
    if not addresses:
        raise RuntimeError('No public IPv4 address was returned. Do not count an internal Tailscale route as a public test.')
    selected = None
    for address in addresses:
        try:
            with public_dns(parsed.hostname, address):
                async with httpx.AsyncClient(timeout=20, trust_env=False) as probe:
                    health = await probe.get(base+'/api/health')
                    health.raise_for_status()
                    if health.json().get('status') == 'ok':
                        selected = address
                        break
        except httpx.HTTPError:
            continue
    if selected is None:
        raise RuntimeError('No public Funnel relay passed the HTTPS health check.')
    report = {'tested_at':datetime.now(timezone.utc).isoformat(), 'url':base,
              'public_dns_addresses':addresses, 'connection_address':selected,
              'tls_certificate_verification':True}
    with public_dns(parsed.hostname, selected):
        async with httpx.AsyncClient(base_url=base, timeout=240, trust_env=False) as client:
            home = await client.get('/')
            home.raise_for_status()
            assert 'F-1 Student Desk' in home.text
            assert (await client.get('/api/messages')).status_code == 401
            assert (await client.get('/api/config')).json()['registration_requires_code'] is True
            denied = await client.post('/api/signup', json={'username':'public-denied-'+uuid4().hex[:8],
                                                           'password':secrets.token_urlsafe(24)})
            assert denied.status_code == 403
            accounts = []
            for suffix in ('a', 'b'):
                credentials = {'username':'public-qa-'+uuid4().hex[:8]+suffix, 'password':secrets.token_urlsafe(24)}
                created = await client.post('/api/signup', json={**credentials, 'registration_code':config.get('REGISTRATION_CODE', '')})
                created.raise_for_status()
                login = await client.post('/api/login', json=credentials)
                login.raise_for_status()
                accounts.append(login.json())
            headers = {'Authorization':'Bearer '+accounts[0]['token']}
            ws_url = 'wss://'+parsed.netloc+'/ws'
            async with websockets.connect(ws_url, origin=base, proxy=None) as a, websockets.connect(ws_url, origin=base, proxy=None) as b:
                for ws, account in zip((a, b), accounts):
                    await ws.send(json.dumps({'token':account['token']}))
                    assert json.loads(await asyncio.wait_for(ws.recv(), 20))['type'] == 'ready'
                normal = await client.post('/api/messages', headers=headers, json={
                    'content':'Public HTTPS QA: two authenticated clients connected.', 'ask_bot':False, 'session_id':str(uuid4())})
                normal.raise_for_status()
                message = normal.json()['message']
                assert normal.json()['reply'] is None
                for ws in (a, b):
                    assert json.loads(await asyncio.wait_for(ws.recv(), 20))['message']['id'] == message['id']
                session_id = str(uuid4())
                answers = []
                for question in ('What is Form 8843 used for?', 'What information does that form ask students to provide?'):
                    response = await client.post('/api/messages', headers=headers,
                        json={'content':question, 'ask_bot':True, 'session_id':session_id})
                    response.raise_for_status()
                    result = response.json()
                    reply = result['reply']
                    assert not reply.get('error_code') and reply['sources'] and not reply.get('citation_warning')
                    assert '8843' in reply['content']
                    assert any(s['source'] == 'irs-f8843.txt' for s in reply['sources'])
                    for ws in (a, b):
                        events = []
                        while True:
                            event = json.loads(await asyncio.wait_for(ws.recv(), 20))
                            events.append(event)
                            if event.get('type') == 'bot_status' and event.get('question_id') == result['message']['id'] and event.get('status') == 'done':
                                break
                        assert any(e.get('status') == 'thinking' for e in events)
                        assert any(e.get('message', {}).get('id') == reply['id'] for e in events)
                    history = await client.get('/api/messages', headers=headers)
                    history.raise_for_status()
                    restored = next(m for m in history.json()['messages'] if m['id'] == reply['id'])
                    assert restored['sources'] == reply['sources']
                    answers.append({'question':question, 'answer':reply['content'], 'sources':reply['sources']})
            assetlinks = await client.get('/.well-known/assetlinks.json')
            assetlinks.raise_for_status()
            assert 'application/json' in assetlinks.headers['content-type']
            report.update({'homepage':200, 'signup_without_invitation':403, 'history_without_login':401,
                'registration_and_login':True, 'two_client_wss_broadcast':True,
                'real_rag_answers':answers, 'sources_persisted':True, 'assetlinks_route':200,
                'android_signature_verified':False})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/a/public-https-smoke.json')
    args = parser.parse_args()
    result = asyncio.run(run(args.base_url.rstrip('/')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Public HTTPS + two-client WSS + real two-turn RAG + persisted sources: passed.')
    print('Certificate verification remained enabled; connected via a public Funnel IPv4 address.')
