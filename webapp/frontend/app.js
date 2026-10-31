'use strict';
const $ = id => document.getElementById(id);
const state = { token: sessionStorage.getItem('desk-token') || '', user: null, ws: null,
  generation: 0, timer: null, ping: null, messages: new Map(), pending: new Set(), pendingRevision: 0, busy: false };
function newSessionId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(x => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
let sessionId = sessionStorage.getItem('desk-session') || newSessionId();
sessionStorage.setItem('desk-session', sessionId);
async function api(path, method = 'GET', body) {
  const response = await fetch('/api' + path, { method,
    headers: { 'Content-Type': 'application/json', ...(state.token ? { Authorization: 'Bearer ' + state.token } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store' });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof result.detail === 'string' ? result.detail : response.status === 422 ? 'Please check the username and password requirements.' : `Request failed (${response.status}).`;
    if (response.status === 401 && !['/login','/signup'].includes(path)) logout('Your session expired. Please log in again.');
    throw new Error(detail);
  }
  return result;
}
function connection(text, offline = false) {
  $('connection').textContent = text;
  $('connection').classList.toggle('offline', offline);
}
function stopSocket() {
  clearTimeout(state.timer); clearInterval(state.ping);
  state.timer = state.ping = null;
  const ws = state.ws; state.ws = null;
  if (ws) { ws.onclose = null; ws.close(); }
}
function logout(message = '') {
  state.generation++; stopSocket(); state.token = ''; state.user = null;
  state.messages.clear(); state.pending.clear(); state.busy = false;
  sessionStorage.removeItem('desk-token');
  sessionId = newSessionId(); sessionStorage.setItem('desk-session', sessionId);
  $('chat').classList.add('hidden'); $('auth').classList.remove('hidden');
  $('connection').classList.add('hidden'); $('authMsg').textContent = message;
  $('password').value = ''; $('chatInput').value = ''; $('chatError').textContent = '';
  setBusy(false); renderMessages();
}
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function sourcePanel(sources) {
  const panel = el('details', 'source-list');
  panel.append(el('summary', '', `${sources.length} retrieved passages · View sources`));
  for (const s of sources) {
    const item = el('div', 'source-item');
    let link = el('span', '', `[${s.number}] ${s.title}`);
    try {
      const url = new URL(s.url);
      if (['https:', 'http:'].includes(url.protocol)) {
        link = el('a', '', `[${s.number}] ${s.title} ↗`);
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
      }
    } catch (_) { /* A source without a public URL still has an excerpt. */ }
    item.append(link, el('p', '', [s.publisher, s.page ? `Page ${s.page}` : '', s.cited ? 'Cited in answer' : 'Retrieved context'].filter(Boolean).join(' · ')));
    const excerpt = el('details'); excerpt.append(el('summary', '', 'Read the passage'), el('blockquote', '', s.excerpt));
    item.append(excerpt); panel.append(item);
  }
  return panel;
}
function messageNode(m) {
  const own = state.user && m.user_id === state.user.user_id;
  const node = el('article', 'message' + (m.is_bot ? ' bot' : '') + (own ? ' mine' : '') + (m.error_code ? ' failed' : ''));
  node.dataset.messageId = m.id;
  const meta = el('div', 'meta');
  meta.append(el('strong', '', m.username || 'Unknown'), el('time', '', m.created_at ? new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : ''));
  node.append(meta);
  if (m.reply_to) {
    const question = state.messages.get(m.reply_to);
    node.append(el('div', 'reply-label', question ? `Reply to ${question.username}: ${question.content.slice(0, 85)}${question.content.length > 85 ? '…' : ''}` : `Reply to question #${m.reply_to}`));
  }
  node.append(el('div', 'message-body', m.content));
  if (m.sources && m.sources.length) node.append(sourcePanel(m.sources));
  if (m.citation_warning) node.append(el('div', 'citation-warning', 'The model did not include numbered citations. Review the retrieved passages before relying on this answer.'));
  if (m.error_code && state.messages.get(m.reply_to)?.user_id === state.user?.user_id) {
    const retry = el('button', 'text-button', 'Retry this question ↗'); retry.type = 'button';
    retry.onclick = async () => {
      retry.disabled = true; $('chatError').textContent = '';
      const generation = state.generation;
      try { const out = await api(`/messages/${m.reply_to}/retry`, 'POST', {session_id: sessionId}); if (generation === state.generation) addMessage(out.reply); }
      catch (e) { if (generation === state.generation) $('chatError').textContent = e.message; }
      finally { retry.disabled = false; }
    };
    node.append(retry);
  }
  return node;
}
function renderMessages() {
  const box = $('messages'); const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 100;
  if (!state.messages.size) {
    box.replaceChildren();
    const empty = el('div', 'empty-state');
    const icon = el('img'); icon.src = '/assets/desk.svg'; icon.alt = ''; icon.width = 56; icon.height = 56;
    empty.append(icon, el('h3', '', 'What would you like to understand?'), el('p', '', 'The assistant searches the document library before answering. Sources appear alongside its response.'));
    box.append(empty); return;
  }
  // Incremental insertion preserves open source disclosures and the user's scroll position.
  const ordered = [...state.messages.values()].sort((a,b) => a.id - b.id);
  box.querySelector('.empty-state')?.remove();
  for (const m of ordered) {
    if (box.querySelector(`[data-message-id="${m.id}"]`)) continue;
    const node = messageNode(m);
    const next = [...box.children].find(child => Number(child.dataset.messageId) > m.id);
    box.insertBefore(node, next || null);
  }
  if (nearBottom) box.scrollTop = box.scrollHeight;
}
function addMessage(m) {
  if (!m) return;
  state.messages.set(m.id, m); renderMessages();
}
function updatePending() {
  $('botStatus').textContent = state.pending.size ? 'Searching the library and preparing a sourced answer…' : '';
}
async function syncMessages(generation) {
  const pendingRevision = state.pendingRevision;
  const out = await api('/messages');
  if (generation !== state.generation) return;
  out.messages.forEach(m => state.messages.set(m.id, m)); renderMessages();
  // HTTP snapshots reconcile a missed done event after reconnection.
  if (pendingRevision === state.pendingRevision) state.pending = new Set(out.pending || []);
  updatePending();
}
function connectWS() {
  if (!state.token) return;
  stopSocket();
  const generation = state.generation;
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  state.ws = ws; connection('Connecting', true);
  ws.onopen = () => ws.send(JSON.stringify({token: state.token}));
  ws.onmessage = async event => {
    if (generation !== state.generation || state.ws !== ws) return;
    let data; try { data = JSON.parse(event.data); } catch (_) { return; }
    if (data.type === 'ready') {
      connection('Live');
      state.ping = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 25000);
      try { await syncMessages(generation); } catch (e) { if (generation === state.generation) $('chatError').textContent = e.message; }
    } else if (data.type === 'message') addMessage(data.message);
    else if (data.type === 'bot_status') {
      state.pendingRevision++;
      if (data.status === 'thinking') state.pending.add(data.question_id); else state.pending.delete(data.question_id);
      updatePending();
    }
  };
  ws.onclose = event => {
    clearInterval(state.ping);
    if (generation !== state.generation || state.ws !== ws || !state.token) return;
    if (event.code === 4401 || event.code === 4403) { logout('Your live connection could not be authorized. Please log in again.'); return; }
    connection('Reconnecting', true); state.timer = setTimeout(connectWS, 2500);
  };
  ws.onerror = () => connection('Connection interrupted', true);
}
async function enterRoom() {
  const generation = ++state.generation;
  const user = await api('/me'); if (generation !== state.generation) return;
  state.user = user; $('accountName').textContent = user.username;
  $('auth').classList.add('hidden'); $('chat').classList.remove('hidden'); $('connection').classList.remove('hidden');
  $('password').value = ''; $('registrationCode').value = ''; $('authMsg').textContent = '';
  $('messages').replaceChildren(); renderMessages();
  try { await syncMessages(generation); }
  catch (e) { if (generation === state.generation) $('chatError').textContent = e.message; }
  if (generation === state.generation) connectWS();
}
async function authenticate(path) {
  if (!$('authForm').reportValidity()) return;
  $('loginBtn').disabled = $('signupBtn').disabled = true; $('authMsg').textContent = '';
  try {
    const out = await api(path, 'POST', {username: $('username').value.trim(), password: $('password').value,
      ...(path === '/signup' ? {registration_code: $('registrationCode').value.trim()} : {})});
    state.token = out.token; sessionStorage.setItem('desk-token', out.token); state.messages.clear(); await enterRoom();
  } catch (e) { $('authMsg').textContent = e.message; }
  finally { $('loginBtn').disabled = $('signupBtn').disabled = false; }
}
function setBusy(busy) { state.busy = busy; $('sendBtn').disabled = busy; $('sendBtn').textContent = busy ? 'Sending…' : 'Send ↑'; $('chatInput').readOnly = busy; $('newSessionBtn').disabled = busy; }
$('authForm').onsubmit = event => { event.preventDefault(); authenticate('/login'); };
$('signupBtn').onclick = () => authenticate('/signup');
$('logoutBtn').onclick = () => logout();
$('newSessionBtn').onclick = () => { sessionId = newSessionId(); sessionStorage.setItem('desk-session', sessionId); $('chatError').textContent = ''; $('botStatus').textContent = 'Fresh session started. Your next question has no previous follow-up context.'; };
$('composer').onsubmit = async event => {
  event.preventDefault(); if (state.busy) return;
  const content = $('chatInput').value.trim(); if (!content) return;
  const generation = state.generation; setBusy(true); $('chatError').textContent = '';
  try {
    const out = await api('/messages', 'POST', {content, ask_bot: $('askBot').checked, session_id: sessionId});
    if (generation !== state.generation) return;
    addMessage(out.message); addMessage(out.reply); $('chatInput').value = '';
  } catch (e) { if (generation === state.generation) $('chatError').textContent = `${e.message} Your draft is preserved. Check the room before resending.`; }
  finally { if (generation === state.generation) { setBusy(false); $('chatInput').focus(); } }
};
$('chatInput').onkeydown = event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('composer').requestSubmit(); } };
document.querySelectorAll('.prompt').forEach(button => button.onclick = () => { if (state.busy) return; $('chatInput').value = button.dataset.prompt; $('askBot').checked = true; $('chatInput').focus(); });
api('/config').then(config => { $('notice').textContent = config.notice; $('corpusInfo').textContent = `${config.source_count} official documents · ${config.chunk_count.toLocaleString()} passages`; $('invitationField').classList.toggle('hidden', !config.registration_requires_code); }).catch(() => {});
if (state.token) enterRoom().catch(e => logout(e.message));
if ('serviceWorker' in navigator && window.isSecureContext) navigator.serviceWorker.register('/sw.js').catch(() => {});
