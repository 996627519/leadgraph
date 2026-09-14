import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable
from backend.persistend.database import users, sessions, metadata, mysql_engine
from backend.service.auth_service import AuthService, PASSWORDS, token_hash
from backend.web.app import create_app
from account_helpers import test_database, login
from test_studio_api import ready_drafts, new_run


@pytest.fixture
def database(tmp_path):
    db = test_database(tmp_path/'accounts.db')
    yield db
    db.close()


def test_anonymous_blocked_and_logout_revokes(database, tmp_path):
    with TestClient(create_app(tmp_path/'graph.db', database=database, demo_delay=0)) as client:
        for path in ['/api/session', '/api/runs', '/api/usage', '/api/runs/missing/events']:
            assert client.get(path).status_code == 401
        user = login(client, register=True)
        token = client.cookies['lg_session']
        assert client.get('/api/session').json()['user'] == user
        stored = database.find_user('tester')
        assert stored['password_hash'].startswith('$argon2id$')
        with database.engine.connect() as db:
            assert db.execute(select(sessions.c.token_hash)).scalar_one() == token_hash(token)
        assert token != token_hash(token)
        response = client.post('/api/auth/logout')
        assert response.status_code == 200
        client.cookies.set('lg_session', token)
        assert client.get('/api/session').status_code == 401


def test_login_csrf_cookie_flags_failure_and_expiration(database, tmp_path):
    with TestClient(create_app(tmp_path/'graph.db', database=database)) as client:
        assert client.post('/api/auth/login', json={'username': 'test', 'password': 'x'}).status_code == 403
        login(client, register=True)
        response = client.post('/api/auth/login', json={'username': 'tester', 'password': 'Test-password-2026'})
        cookies = response.headers.get_list('set-cookie')
        assert all('HttpOnly' in c and 'SameSite=strict' in c for c in cookies)
        client.headers['X-Studio-Token'] = response.json()['token']
        failed = client.post('/api/auth/login', json={'username': 'tester', 'password': 'wrong'})
        missing = client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong'})
        assert failed.status_code == missing.status_code == 401
        assert failed.json() == missing.json()
        with database.engine.begin() as db:
            db.execute(update(sessions).values(expires_at=int(time.time())-1))
        assert client.get('/api/runs').status_code == 401


def test_other_user_cannot_read_or_resume_any_run(database, tmp_path):
    with TestClient(create_app(tmp_path/'graph.db', database=database, demo_delay=0)) as client:
        owner = login(client, register=True)
        run = new_run(client)
        assert run['user_id'] == owner['id']
        login(client, 'second_user', register=True)
        assert client.get('/api/runs').json() == []
        base = '/api/runs/' + run['id']
        for suffix in ['', '/events']:
            assert client.get(base+suffix).status_code == 404
        for suffix in ['/cancel', '/continue', '/contacts', '/drafts', '/send', '/skip-send']:
            assert client.post(base+suffix, json={'confirmed': True}).status_code == 404
        assert client.patch(base+'/drafts/any', json={}).status_code == 404
        assert client.patch(base+'/contacts/any', json={}).status_code == 404
        login(client)
        assert client.get(base).status_code == 200
        assert len(client.get('/api/runs').json()) == 1


def test_closed_registration_and_throttling(database, tmp_path, monkeypatch):
    monkeypatch.setenv('ALLOW_REGISTRATION', 'false')
    with TestClient(create_app(tmp_path/'graph.db', database=database)) as client:
        data = client.get('/api/auth/csrf').json()
        assert data['registration_enabled'] is False
        client.headers['X-Studio-Token'] = data['token']
        assert client.post('/api/auth/register', json={'username':'tester','password':'Test-password-2026'}).status_code == 403
        for _ in range(8):
            assert client.post('/api/auth/login', json={'username':'tester','password':'wrong'}).status_code == 401
        assert client.post('/api/auth/login', json={'username':'tester','password':'wrong'}).status_code == 429


def test_skip_ends_checkpoint_without_transport_and_survives_restart(database, tmp_path):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Skip must not call SMTP')
    path = tmp_path/'graph.db'
    with TestClient(create_app(path, database=database, demo_delay=0, send_fn=forbidden)) as client:
        login(client, register=True)
        run = ready_drafts(client)
        endpoint = '/api/runs/' + run['id']
        assert client.post(endpoint+'/skip-send', json={'confirmed': False}).status_code == 422
        result = client.post(endpoint+'/skip-send', json={'confirmed': True})
        assert result.status_code == 200
        final = result.json()
        assert final['outreach_status'] == 'skipped'
        assert final['graph_next'] == [] and final['interrupt_kind'] is None
        assert all(d['status'] == 'skipped' for d in final['drafts'])
        assert client.post(endpoint+'/skip-send', json={'confirmed': True}).status_code == 200
        payload = {'confirmed': True, 'drafts': [{'id': d['id'], 'revision': d['revision']} for d in final['drafts']]}
        assert client.post(endpoint+'/send', json=payload).status_code == 409
        assert client.post(endpoint+'/continue').status_code == 409
        assert database.delivery_results(run['id']) == {}
    with TestClient(create_app(path, database=database, demo_delay=0, send_fn=forbidden)) as client:
        login(client)
        restored = client.get(endpoint).json()
        assert restored['outreach_status'] == 'skipped' and restored['graph_next'] == []
    assert calls == []


def test_production_engine_requires_mysql_and_ddl_compiles(monkeypatch):
    monkeypatch.delenv('MYSQL_USER', raising=False)
    with pytest.raises(RuntimeError, match='MYSQL_USER'):
        mysql_engine()
    monkeypatch.setenv('MYSQL_USER', 'example')
    monkeypatch.setenv('MYSQL_PASSWORD', 'special@:# password')
    engine = mysql_engine()
    assert engine.dialect.name == 'mysql'
    assert engine.url.password == 'special@:# password'
    for table in metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=mysql.dialect()))
    engine.dispose()
