import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from shared.config import ROOT
from webapp.backend.rag_service import ServiceError, answer_with_sources
from webapp.backend.public_access import PublicAccess

PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / 'frontend'
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat')
JWT_SECRET = os.getenv('JWT_SECRET', '')
JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '1440'))
public_access = PublicAccess(os.getenv('PUBLIC_MODE', '').lower() == 'true',
                             os.getenv('REGISTRATION_CODE', ''))
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
if len(JWT_SECRET) < 32 or JWT_SECRET == 'please_change_me_to_a_long_random_value':
    raise RuntimeError('Set a unique JWT_SECRET of at least 32 characters in root .env.')
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
# Retain verification for template bcrypt accounts; new hashes support Unicode/long passwords.
passwords = CryptContext(schemes=['pbkdf2_sha256', 'bcrypt'], deprecated='auto')
log = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class MessageDetails(Base):
    # A companion table upgrades the original template without ALTERing/deleting messages.
    __tablename__ = 'message_details'
    message_id: Mapped[int] = mapped_column(ForeignKey('messages.id', ondelete='CASCADE'), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r'^[\w.-]+$')
    password: str = Field(min_length=8, max_length=128)
    @field_validator('username', mode='before')
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value

class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    ask_bot: bool = False
    session_id: UUID

class SignupCredentials(Credentials):
    registration_code: str = Field(default='', max_length=256)

class RetryMessage(BaseModel):
    session_id: UUID

async def get_session():
    async with SessionLocal() as session:
        yield session

def make_token(user):
    return jwt.encode({'sub': str(user.id), 'username': user.username,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)}, JWT_SECRET, algorithm='HS256')

def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'], options={'require_exp': True})
        return int(payload['sub']), float(payload['exp'])
    except (JWTError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(401, 'Invalid or expired login token') from exc

async def current_user(authorization: Optional[str] = Header(default=None), session: AsyncSession = Depends(get_session)):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'Please log in to continue')
    user_id, _ = decode_token(authorization.split(' ', 1)[1])
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(401, 'User no longer exists')
    return user

class ConnectionManager:
    def __init__(self):
        self.connections = {}
    async def send(self, websocket, data):
        lock = self.connections.get(websocket)
        if lock is None:
            return
        try:
            async with lock:
                await asyncio.wait_for(websocket.send_json(data), 5)
        except Exception:
            self.disconnect(websocket)
    async def broadcast(self, data):
        await asyncio.gather(*(self.send(ws, data) for ws in list(self.connections)))
    def disconnect(self, websocket):
        self.connections.pop(websocket, None)

manager = ConnectionManager()
# This class lab uses one Uvicorn worker; see deployment guide for that requirement.
active_questions = set()

def message_json(message, username, details=None):
    created = message.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {'id': message.id, 'user_id': message.user_id, 'username': username,
            'content': message.content, 'is_bot': message.is_bot,
            'created_at': created.isoformat() if created else None,
            **(json.loads(details.payload) if details else {})}

async def save_message(content, user_id, is_bot, username, **metadata):
    async with SessionLocal() as session:
        message = Message(content=content, user_id=user_id, is_bot=is_bot,
                          created_at=datetime.now(timezone.utc).replace(tzinfo=None))
        session.add(message)
        await session.flush()
        details = MessageDetails(message_id=message.id, payload=json.dumps(metadata, ensure_ascii=False))
        session.add(details)
        await session.commit()
        await session.refresh(message)
        return message_json(message, username, details)

async def ask_llm(question: str, session_id: str):
    return await answer_with_sources(question, session_id)

async def answer_question(saved, user_id, session_id):
    key = saved['id']
    if key in active_questions:
        raise HTTPException(409, 'This question is already being answered')
    active_questions.add(key)
    await manager.broadcast({'type': 'bot_status', 'question_id': key, 'status': 'thinking'})
    try:
        try:
            result = await ask_llm(saved['content'], f'{user_id}:{session_id}')
            bot = await save_message(result['answer'], None, True, 'Student Desk',
                reply_to=key, sources=result['sources'], notice=result.get('notice'),
                citation_warning=result.get('citation_warning', False), error_code=None)
        except ServiceError as exc:
            bot = await save_message(str(exc), None, True, 'Student Desk',
                                    reply_to=key, sources=[], error_code=exc.code)
        except Exception:
            # Do not expose URLs, API keys or database diagnostics to chat participants.
            log.error('Assistant request failed (question_id=%s)', key)
            bot = await save_message('The assistant encountered an unexpected error. Please retry.',
                                    None, True, 'Student Desk', reply_to=key, sources=[], error_code='internal_error')
        await manager.broadcast({'type': 'message', 'message': bot})
        return bot
    finally:
        active_questions.discard(key)
        await manager.broadcast({'type': 'bot_status', 'question_id': key, 'status': 'done'})

@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    for ws in list(manager.connections):
        await ws.close(code=1001)
    manager.connections.clear()
    await engine.dispose()

app = FastAPI(title='F-1 Student Desk', lifespan=lifespan)
app.mount('/.well-known', StaticFiles(directory=FRONTEND_DIR/'.well-known'), name='well-known')
app.mount('/assets', StaticFiles(directory=FRONTEND_DIR/'assets'), name='assets')

@app.middleware('http')
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    if request.url.path == '/':
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    return response

@app.get('/')
async def home():
    return FileResponse(FRONTEND_DIR/'index.html')

@app.get('/styles.css')
async def styles():
    return FileResponse(FRONTEND_DIR/'styles.css', media_type='text/css')

@app.get('/app.js')
async def javascript():
    return FileResponse(FRONTEND_DIR/'app.js', media_type='application/javascript')

@app.get('/manifest.webmanifest')
async def manifest():
    return FileResponse(FRONTEND_DIR/'manifest.webmanifest', media_type='application/manifest+json')

@app.get('/sw.js')
async def service_worker():
    return FileResponse(FRONTEND_DIR/'sw.js', media_type='application/javascript', headers={'Cache-Control': 'no-cache'})

@app.get('/api/config')
async def public_config():
    sources = json.loads((ROOT/'data/topic/sources.json').read_text(encoding='utf-8'))
    manifest = json.loads((ROOT/'data/topic/index/manifest.json').read_text(encoding='utf-8'))
    return {'notice': sources['notice'], 'source_count': len(sources['sources']),
            'chunk_count': manifest['count'], 'room': 'Shared study room',
            'registration_requires_code': public_access.enabled}

@app.get('/api/health')
async def health(session: AsyncSession = Depends(get_session)):
    await session.execute(select(1))
    return {'status': 'ok', 'database': engine.dialect.name,
            'openai_key_configured': bool(os.getenv('OPENAI_API_KEY', '').strip()),
            'llm_configured': bool(os.getenv('LLM_API_BASE', '').strip())}

@app.post('/api/signup')
async def signup(data: SignupCredentials, session: AsyncSession = Depends(get_session)):
    public_access.auth(data.username)
    public_access.check_invitation(data.registration_code)
    user = User(username=data.username, password_hash=await asyncio.to_thread(passwords.hash, data.password),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, 'Username is already taken')
    await session.refresh(user)
    return {'token': make_token(user), 'username': user.username, 'user_id': user.id}

@app.post('/api/login')
async def login(data: Credentials, session: AsyncSession = Depends(get_session)):
    public_access.auth(data.username)
    user = await session.scalar(select(User).where(User.username == data.username))
    valid = False
    if user:
        try:
            valid = await asyncio.to_thread(passwords.verify, data.password, user.password_hash)
        except ValueError:
            pass
    if not valid:
        raise HTTPException(401, 'Incorrect username or password')
    return {'token': make_token(user), 'username': user.username, 'user_id': user.id}

@app.get('/api/me')
async def me(user: User = Depends(current_user)):
    return {'username': user.username, 'user_id': user.id}

@app.get('/api/messages')
async def get_messages(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Message, User.username, MessageDetails)
        .outerjoin(User, Message.user_id == User.id)
        .outerjoin(MessageDetails, Message.id == MessageDetails.message_id)
        .order_by(Message.id.desc()).limit(100))).all()
    return {'messages': [message_json(m, 'Student Desk' if m.is_bot else (name or 'unknown'), details)
                         for m, name, details in reversed(rows)], 'pending': sorted(active_questions)}

@app.post('/api/messages')
async def post_message(data: NewMessage, user: User = Depends(current_user)):
    content = data.content.strip()
    if not content:
        raise HTTPException(400, 'Message cannot be blank')
    ask_bot = data.ask_bot or '?' in content or '？' in content
    with public_access.message(user.id, ask_bot):
        saved = await save_message(content, user.id, False, user.username, ask_bot=ask_bot)
        await manager.broadcast({'type': 'message', 'message': saved})
        reply = await answer_question(saved, user.id, data.session_id) if ask_bot else None
    return {'message': saved, 'reply': reply}

@app.post('/api/messages/{message_id}/retry')
async def retry_message(message_id: int, data: RetryMessage, user: User = Depends(current_user),
                        session: AsyncSession = Depends(get_session)):
    message = await session.get(Message, message_id)
    details = await session.get(MessageDetails, message_id)
    if not message or message.is_bot or message.user_id != user.id:
        raise HTTPException(404, 'Question not found')
    if not details or not json.loads(details.payload).get('ask_bot'):
        raise HTTPException(400, 'This message was not a question for the assistant')
    if message_id in active_questions:
        raise HTTPException(409, 'This question is already being answered')
    with public_access.message(user.id, True):
        reply = await answer_question(message_json(message, user.username), user.id, data.session_id)
    return {'reply': reply}

@app.websocket('/ws')
async def websocket_chat(websocket: WebSocket):
    # Browser Origin must match the served host. Credentials travel in the first
    # frame, never in the URL (which a reverse proxy might log).
    origin = websocket.headers.get('origin')
    host = websocket.headers.get('host')
    if origin and origin not in (f'http://{host}', f'https://{host}', PUBLIC_ORIGIN):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        auth = await asyncio.wait_for(websocket.receive_json(), 10)
        user_id, expiry = decode_token(auth.get('token', ''))
        async with SessionLocal() as session:
            if await session.get(User, user_id) is None:
                raise HTTPException(401, 'User no longer exists')
        manager.connections[websocket] = asyncio.Lock()
        await manager.send(websocket, {'type': 'ready'})
        while True:
            remaining = expiry - datetime.now(timezone.utc).timestamp()
            if remaining <= 0:
                await websocket.close(code=4401)
                break
            await asyncio.wait_for(websocket.receive_text(), remaining)
    except (HTTPException, ValueError, TypeError, AttributeError):
        await websocket.close(code=4401)
    except asyncio.TimeoutError:
        await websocket.close(code=4401)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
