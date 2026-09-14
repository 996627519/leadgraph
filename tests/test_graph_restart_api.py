#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_graph_restart_api.py
@Author ：zlh
@Date ：2026-09-14 10:44 
"""
from fastapi.testclient import TestClient
from backend.web.app import create_app
from account_helpers import test_database, login
from test_studio_api import ready_drafts, ready_contacts, wait_run


def test_api_restart_restores_graph_not_just_display_records(tmp_path):
    path = tmp_path/'studio.db'
    database = test_database(tmp_path/'accounts.db')
    database.create_user('tester', __import__('backend.service.auth_service', fromlist=['PASSWORDS']).PASSWORDS.hash('Test-password-2026'))
    with TestClient(create_app(path, database=database, demo_delay=0)) as client:
        login(client)
        run, ids = ready_contacts(client)
        run_id = run['id']
    with TestClient(create_app(path, database=database, demo_delay=0)) as client:
        login(client)
        restored = client.get('/api/runs/' + run_id).json()
        assert restored['interrupt_kind'] == 'contacts'
        assert restored['graph_next'] == ['contact_review']
        response = client.post(f'/api/runs/{run_id}/drafts', json={
            'lead_ids': ids, 'keywords': '设备合作，邀请交流', 'signature': 'Example',
        })
        assert response.status_code == 202
        run = wait_run(client, run_id, lambda r: r['status'] == 'compose')
        assert run['graph_next'] == ['mail_review']
    with TestClient(create_app(path, database=database, demo_delay=0)) as client:
        login(client)
        run = client.get('/api/runs/' + run_id).json()
        payload = {'confirmed': True, 'drafts': [{'id': d['id'], 'revision': d['revision']} for d in run['drafts']]}
        assert client.post(f'/api/runs/{run_id}/send', json=payload).status_code == 202
        final = wait_run(client, run_id, lambda r: r['status'] == 'compose' and all(d['status'] == 'simulated' for d in r['drafts']))
        assert final['graph_next'] == []


def test_mail_failure_keeps_other_results_and_never_auto_retries(tmp_path):
    database = test_database(tmp_path/'accounts.db')
    database.create_user('tester', __import__('backend.service.auth_service', fromlist=['PASSWORDS']).PASSWORDS.hash('Test-password-2026'))
    calls = []
    def transport(draft, *, demo):
        calls.append(draft['id'])
        return {'status': 'unknown' if len(calls) == 1 else 'simulated'}
    with TestClient(create_app(tmp_path/'failure.db', database=database, demo_delay=0, send_fn=transport)) as client:
        login(client)
        run = ready_drafts(client)
        payload = {'confirmed': True, 'drafts': [{'id': d['id'], 'revision': 1} for d in run['drafts']]}
        assert client.post(f'/api/runs/{run["id"]}/send', json=payload).status_code == 202
        final = wait_run(client, run['id'], lambda r: r['status'] == 'compose')
        assert [d['status'] for d in final['drafts']] == ['unknown', 'simulated']
        assert client.post(f'/api/runs/{run["id"]}/send', json=payload).status_code == 409
        assert len(calls) == 2
