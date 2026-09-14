"""Argon2 密码摘要与可撤销服务端会话；浏览器只保存 HttpOnly 随机会话令牌。"""
import hashlib
import re
import secrets
import time
import threading
from collections import defaultdict, deque
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

PASSWORDS = PasswordHasher()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(24))


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


class RateLimitError(ValueError):
    pass


class AuthService:
    def __init__(self, database, *, ttl=8*3600):
        self.database, self.ttl = database, ttl
        self.attempts = defaultdict(deque)
        self.lock = threading.Lock()

    def limit(self, ip, username, *, register=False):
        current = time.monotonic()
        pairs = [(('ip', ip), 40), (('user', ip, username.casefold()), 8)]
        if register:
            pairs = [(('register', ip), 5)]
        with self.lock:
            if len(self.attempts) > 10000:
                for key in list(self.attempts):
                    if not self.attempts[key] or self.attempts[key][-1] < current-300:
                        del self.attempts[key]
            for key, maximum in pairs:
                queue = self.attempts[key]
                while queue and queue[0] < current-300:
                    queue.popleft()
                if len(queue) >= maximum:
                    raise RateLimitError('尝试次数较多，请稍后再试。')
            for key, _ in pairs:
                self.attempts[key].append(current)

    def register(self, username, password):
        username = username.strip().casefold()
        if not re.fullmatch(r'[a-z0-9_][a-z0-9_.-]{2,31}', username):
            raise ValueError('用户名需为 3–32 位字母、数字、下划线、点或短横线。')
        if not 10 <= len(password) <= 128:
            raise ValueError('密码长度需为 10–128 位。')
        return self.database.create_user(username, PASSWORDS.hash(password))

    def login(self, username, password):
        user = self.database.find_user(username.strip().casefold())
        try:
            valid = PASSWORDS.verify(user['password_hash'] if user else DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            valid = False
        if not valid or not user or not user['active']:
            raise ValueError('用户名或密码不正确。')
        token = secrets.token_urlsafe(32)
        self.database.save_session(token_hash(token), user['id'], int(time.time())+self.ttl)
        return token, {'id': user['id'], 'username': user['username']}

    def current(self, token):
        if not token or len(token) > 200:
            return None
        return self.database.get_session(token_hash(token), int(time.time()))

    def logout(self, token):
        if token:
            self.database.delete_session(token_hash(token))
