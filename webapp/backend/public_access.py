"""Small, process-local guards for the single-worker class demo."""
from collections import deque
from contextlib import contextmanager
import math
import secrets
import time

from fastapi import HTTPException


class PublicAccess:
    def __init__(self, enabled=False, registration_code='', clock=time.monotonic):
        if enabled and len(registration_code) < 16:
            raise RuntimeError('PUBLIC_MODE requires a REGISTRATION_CODE of at least 16 characters.')
        self.enabled = enabled
        self.registration_code = registration_code
        self.clock = clock
        self.events = {}
        self.active = 0

    def check_invitation(self, supplied):
        if self.enabled and not secrets.compare_digest(
                self.registration_code.encode(), supplied.encode()):
            raise HTTPException(403, 'A valid group invitation code is required to create an account.')

    def _consume(self, rules):
        # No await: checking and reserving is atomic on the one ASGI event loop.
        now = self.clock()
        for key, (window, events) in list(self.events.items()):
            while events and events[0] <= now - window:
                events.popleft()
            if not events:
                del self.events[key]
        for key, limit, window in rules:
            events = self.events.get(key, (window, ()))[1]
            if len(events) >= limit:
                delay = max(1, math.ceil(events[0] + window - now))
                raise HTTPException(429, f'Too many requests. Try again in {delay} seconds.',
                                    headers={'Retry-After': str(delay)})
        for key, _, window in rules:
            self.events.setdefault(key, (window, deque()))[1].append(now)

    def auth(self, username):
        if self.enabled:
            # Global limit also bounds distinct user-name buckets; no forwarded-IP trust.
            self._consume([('auth:all', 60, 60), ('auth:'+username.casefold(), 10, 60)])

    @contextmanager
    def message(self, user_id, assistant):
        if not self.enabled:
            yield
            return
        if assistant and self.active >= 1:
            raise HTTPException(429, 'The assistant is answering another question. Please try again shortly.',
                                headers={'Retry-After': '5'})
        rules = [('message:all', 120, 60), (f'message:{user_id}', 30, 60)]
        if assistant:
            rules += [('assistant:all', 60, 3600), (f'assistant:{user_id}', 6, 60)]
        self._consume(rules)
        if assistant:
            self.active += 1
        try:
            yield
        finally:
            if assistant:
                self.active -= 1
