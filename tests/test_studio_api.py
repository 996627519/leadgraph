#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_studio_api.py
@Author ：zlh
@Date ：2026-09-14 10:46 
"""
import time
import pytest
from fastapi.testclient import TestClient
from backend.web.app import create_app
from account_helpers import test_database, login


@pytest.fixture
def client(tmp_path):
    database = test_database(tmp_path/'accounts.db')
    with TestClient(create_app(tmp_path/'test.db',database=database,demo_delay=0)) as c:
        login(c, register=True)
        yield c
    database.close()


def wait_run(client,run_id,predicate):
    until=time.monotonic()+5
    while time.monotonic()<until:
        data=client.get('/api/runs/'+run_id).json()
        if predicate(data): return data
        time.sleep(.02)
    raise AssertionError(data)


def new_run(client):
    response=client.post('/api/runs',json={'query':'寻找英国乳制品公司的工程经理','mode':'demo'})
    assert response.status_code==202
    return wait_run(client,response.json()['id'],lambda r:r['status']=='review')


def ready_contacts(client):
    run=new_run(client)
    ids=[l['id'] for l in run['leads'][:2]]
    assert client.post(f'/api/runs/{run["id"]}/contacts',json={'lead_ids':ids}).status_code==202
    run=wait_run(client,run['id'],lambda r:r['status']=='contacts')
    for lead_id in ids:
        response=client.patch(f'/api/runs/{run["id"]}/contacts/{lead_id}',json={'email':run['contacts'][lead_id]['candidates'][0]['email'],'confirmed':True})
        assert response.status_code==200
    return client.get('/api/runs/'+run['id']).json(),ids


def ready_drafts(client):
    run,ids=ready_contacts(client)
    response=client.post(f'/api/runs/{run["id"]}/drafts',json={'lead_ids':ids,'keywords':'牛奶消毒设备，邀请简短交流','signature':'林 · Example Equipment','language':'en','tone':'friendly'})
    assert response.status_code==202
    return wait_run(client,run['id'],lambda r:r['status']=='compose')


def test_demo_entire_flow_edit_confirm_and_idempotent_send(client):
    run=ready_drafts(client)
    draft=run['drafts'][0]
    edited=client.patch(f'/api/runs/{run["id"]}/drafts/{draft["id"]}',json={'revision':1,'subject':'A personal introduction','body':'Hello, a reviewed message.\nBest regards.'})
    assert edited.status_code==200
    run=edited.json()
    assert run['drafts'][0]['revision']==2
    payload={'confirmed':True,'drafts':[{'id':d['id'],'revision':d['revision']} for d in run['drafts']]}
    first=client.post(f'/api/runs/{run["id"]}/send',json=payload)
    assert first.status_code==202
    final=wait_run(client,run['id'],lambda r:all(d['status']=='simulated' for d in r['drafts']))
    message_ids=[d['message_id'] for d in final['drafts']]
    assert client.post(f'/api/runs/{run["id"]}/send',json=payload).status_code==202
    again=client.get('/api/runs/'+run['id']).json()
    assert [d['message_id'] for d in again['drafts']]==message_ids
    assert len([e for e in again['events'] if e['title']=='邮件提交结果已记录'])==2


def test_mutations_require_session_and_origin(client):
    assert client.post('/api/runs',headers={'X-Studio-Token':''},json={'query':'test query'}).status_code==403
    assert client.post('/api/runs',headers={'Origin':'https://evil.example'},json={'query':'test query'}).status_code==403


def test_cannot_lookup_unselected_unknown_lead(client):
    run=new_run(client)
    assert client.post(f'/api/runs/{run["id"]}/contacts',json={'lead_ids':['unknown']}).status_code==409


def test_contact_confirmation_rejects_header_injection(client):
    run,ids=ready_contacts(client)
    assert client.patch(f'/api/runs/{run["id"]}/contacts/{ids[0]}',json={'email':'a@example.com\r\nBcc: b@example.com','confirmed':True}).status_code==409


def test_email_generation_requires_confirmed_contact(client):
    run=new_run(client)
    response=client.post(f'/api/runs/{run["id"]}/drafts',json={'lead_ids':[run['leads'][0]['id']],'keywords':'设备合作','signature':'Example'})
    assert response.status_code==409


def test_send_requires_explicit_confirmation_and_exact_revision(client):
    run=ready_drafts(client)
    draft=run['drafts'][0]
    path=f'/api/runs/{run["id"]}/send'
    assert client.post(path,json={'drafts':[{'id':draft['id'],'revision':1}]}).status_code==422
    assert client.post(path,json={'confirmed':False,'drafts':[{'id':draft['id'],'revision':1}]}).status_code==422
    assert client.post(path,json={'confirmed':True,'drafts':[{'id':draft['id'],'revision':9}]}).status_code==409
    assert client.get('/api/runs/'+run['id']).json()['drafts'][0]['status']=='draft'


def test_edit_and_recipient_mutation_blocked_after_send(client):
    run=ready_drafts(client);draft=run['drafts'][0]
    client.post(f'/api/runs/{run["id"]}/send',json={'confirmed':True,'drafts':[{'id':draft['id'],'revision':1}]})
    wait_run(client,run['id'],lambda r:r['drafts'][0]['status']=='simulated')
    assert client.patch(f'/api/runs/{run["id"]}/drafts/{draft["id"]}',json={'revision':1,'subject':'Changed','body':'Changed'}).status_code==409
    assert client.patch(f'/api/runs/{run["id"]}/contacts/{draft["lead_id"]}',json={'email':'other@example.com','confirmed':True}).status_code==409


def test_manual_email_path_for_not_found_contact(client):
    run=new_run(client);lead=run['leads'][2]
    client.post(f'/api/runs/{run["id"]}/contacts',json={'lead_ids':[lead['id']]})
    run=wait_run(client,run['id'],lambda r:r['status']=='contacts')
    assert run['contacts'][lead['id']]['status']=='not_found'
    response=client.patch(f'/api/runs/{run["id"]}/contacts/{lead["id"]}',json={'email':'known@example.com','confirmed':True})
    assert response.json()['contacts'][lead['id']]['origin']=='manual'


def test_static_page_and_sse(client):
    assert 'LeadGraph Studio' in client.get('/').text
    assert client.get('/assets/app.js').status_code==200
    run=new_run(client)
    response=client.get(f'/api/runs/{run["id"]}/events')
    assert 'event: progress' in response.text
    assert 'event: snapshot' in response.text
    assert 'review' in response.text


def test_store_recovers_interrupted_send_as_unknown(tmp_path):
    from backend.persistend.studio_store import Store
    path=tmp_path/'recovery.db';store=Store(path)
    store.create({'id':'x','status':'drafting','drafts':[{'id':'d','status':'sending'}]})
    store.recover_interrupted()
    result=store.get('x')
    assert result['status']=='interrupted'
    assert result['drafts'][0]['status']=='unknown'
