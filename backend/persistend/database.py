"""MySQL 业务仓库。生产入口只接受 MySQL；测试显式注入 SQLite Engine。"""
import os
from copy import deepcopy
from uuid import uuid4
from sqlalchemy import (MetaData, Table, Column, String, BigInteger, Boolean,
                        JSON, ForeignKey, UniqueConstraint, create_engine, select, update, delete)
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from backend.persistend.studio_store import now

metadata = MetaData()
users = Table('lg_users', metadata,
    Column('id', String(32), primary_key=True), Column('username', String(64), nullable=False, unique=True),
    Column('password_hash', String(255), nullable=False), Column('active', Boolean, nullable=False, default=True),
    Column('created_at', String(40), nullable=False))
sessions = Table('lg_sessions', metadata,
    Column('token_hash', String(64), primary_key=True),
    Column('user_id', String(32), ForeignKey('lg_users.id'), nullable=False, index=True),
    Column('expires_at', BigInteger, nullable=False, index=True))
runs = Table('lg_runs', metadata,
    Column('id', String(32), primary_key=True),
    Column('user_id', String(32), ForeignKey('lg_users.id'), nullable=False, index=True),
    Column('created_at', String(40), nullable=False, index=True), Column('payload', JSON, nullable=False))
deliveries = Table('lg_deliveries', metadata,
    Column('run_id', String(32), ForeignKey('lg_runs.id'), primary_key=True),
    Column('draft_id', String(32), primary_key=True), Column('recipient', String(254), nullable=False),
    Column('digest', String(64), nullable=False), Column('result', JSON, nullable=False),
    UniqueConstraint('run_id', 'recipient', name='uq_run_recipient'))


def mysql_engine():
    user = os.getenv('MYSQL_USER', '')
    if not user:
        raise RuntimeError('请配置 MYSQL_USER / MYSQL_PASSWORD，并按 docs/ACCOUNT_SETUP.md 初始化 MySQL。')
    url = URL.create('mysql+pymysql', username=user, password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', '127.0.0.1'), port=int(os.getenv('MYSQL_PORT', '3306')),
        database=os.getenv('MYSQL_DATABASE', 'leadgraph'), query={'charset': 'utf8mb4'})
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=5, max_overflow=5,
                         connect_args={'connect_timeout': 5, 'read_timeout': 10, 'write_timeout': 10})


class Database:
    def __init__(self, engine=None):
        self.engine = engine if engine is not None else mysql_engine()

    def initialize(self):
        metadata.create_all(self.engine)

    def check(self):
        with self.engine.connect() as db:
            db.execute(select(users.c.id).limit(1))

    def close(self):
        self.engine.dispose()

    def create_user(self, username, password_hash):
        user_id = uuid4().hex
        try:
            with self.engine.begin() as db:
                db.execute(users.insert().values(id=user_id, username=username, password_hash=password_hash,
                                                active=True, created_at=now()))
        except IntegrityError:
            raise ValueError('该用户名已被使用。') from None
        return {'id': user_id, 'username': username}

    def find_user(self, username):
        with self.engine.connect() as db:
            row = db.execute(select(users).where(users.c.username == username)).mappings().first()
            return dict(row) if row else None

    def save_session(self, token_hash, user_id, expires_at):
        with self.engine.begin() as db:
            db.execute(sessions.insert().values(token_hash=token_hash, user_id=user_id, expires_at=expires_at))

    def get_session(self, token_hash, timestamp):
        with self.engine.connect() as db:
            row = db.execute(select(users.c.id, users.c.username).join(sessions, users.c.id == sessions.c.user_id)
                .where(sessions.c.token_hash == token_hash, sessions.c.expires_at > timestamp, users.c.active.is_(True))).mappings().first()
            return dict(row) if row else None

    def delete_session(self, token_hash):
        with self.engine.begin() as db:
            db.execute(delete(sessions).where(sessions.c.token_hash == token_hash))

    def prune_sessions(self, timestamp):
        with self.engine.begin() as db:
            db.execute(delete(sessions).where(sessions.c.expires_at <= timestamp))

    def create(self, run):
        with self.engine.begin() as db:
            db.execute(runs.insert().values(id=run['id'], user_id=run['user_id'], created_at=run['created_at'], payload=run))
        return run

    def get(self, run_id):
        with self.engine.connect() as db:
            result = db.execute(select(runs.c.payload).where(runs.c.id == run_id)).scalar_one_or_none()
        if result is None:
            raise KeyError(run_id)
        return deepcopy(result)

    def get_owned(self, run_id, user_id):
        with self.engine.connect() as db:
            result = db.execute(select(runs.c.payload).where(runs.c.id == run_id, runs.c.user_id == user_id)).scalar_one_or_none()
        if result is None:
            raise KeyError(run_id)
        return deepcopy(result)

    def list(self, limit=100, *, user_id=None):
        query = select(runs.c.payload).order_by(runs.c.created_at.desc())
        if user_id is not None:
            query = query.where(runs.c.user_id == user_id)
        if limit is not None:
            query = query.limit(max(0, int(limit)))
        with self.engine.connect() as db:
            return [deepcopy(row[0]) for row in db.execute(query)]

    def mutate(self, run_id, fn):
        with self.engine.begin() as db:
            # SQLite 测试引擎没有 FOR UPDATE，显式领取写锁模拟串行更新。
            if self.engine.dialect.name == 'sqlite':
                db.exec_driver_sql('BEGIN IMMEDIATE')
            value = db.execute(select(runs.c.payload).where(runs.c.id == run_id).with_for_update()).scalar_one_or_none()
            if value is None:
                raise KeyError(run_id)
            run = deepcopy(value)
            result = fn(run)
            run['updated_at'] = now()
            run['version'] = run.get('version', 0) + 1
            db.execute(update(runs).where(runs.c.id == run_id).values(payload=run))
            return result

    def claim_delivery(self, run_id, draft, digest):
        try:
            with self.engine.begin() as db:
                db.execute(deliveries.insert().values(run_id=run_id, draft_id=draft['id'],
                    recipient=draft['recipient'].casefold(), digest=digest, result={'status': 'sending'}))
            return None  # 事务提交后才能执行 SMTP。
        except IntegrityError:
            with self.engine.connect() as db:
                row = db.execute(select(deliveries).where(deliveries.c.run_id == run_id,
                    deliveries.c.draft_id == draft['id'])).mappings().first()
            if row is None or row['digest'] != digest:
                raise ValueError('已有相同收件地址或其他版本的发送记录。') from None
            result = row['result']
            if result['status'] == 'sending':
                return {'status': 'unknown', 'error': '已进入发送但结果尚未确认，请核查发件记录。'}
            return result

    def finish_delivery(self, run_id, draft_id, result):
        with self.engine.begin() as db:
            db.execute(update(deliveries).where(deliveries.c.run_id == run_id, deliveries.c.draft_id == draft_id).values(result=result))

    def delivery_results(self, run_id):
        with self.engine.connect() as db:
            return {row[0]: row[1] for row in db.execute(select(deliveries.c.draft_id, deliveries.c.result).where(deliveries.c.run_id == run_id))}
