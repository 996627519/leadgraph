"""只用于测试的数据库和登录助手；生产入口不会回退到此数据库。"""
from sqlalchemy import create_engine, event
from backend.persistend.database import Database


def test_database(path):
    engine = create_engine('sqlite:///' + str(path), connect_args={'check_same_thread': False})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    database = Database(engine)
    database.initialize()
    return database


def login(client, username='tester', password='Test-password-2026', *, register=False):
    client.headers['X-Studio-Token'] = client.get('/api/auth/csrf').json()['token']
    if register:
        response = client.post('/api/auth/register', json={'username': username, 'password': password})
        assert response.status_code == 201, response.text
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200, response.text
    client.headers['X-Studio-Token'] = response.json()['token']
    return response.json()['user']


test_database.__test__ = False
