#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_outreach_graph.py
@Author ：zlh
@Date ：2026-09-14 10:45 
"""
import sqlite3
import json
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from backend.graph.main_graph import create_graph
from backend.service.workflow_services import WorkflowServices
from backend.service.email_service import EmailService, draft_digest
from backend.config.settings import Settings
from backend.service.search_service import SearchService
from examples.demo_services import DemoModel, DemoSearch


def services(tmp_path, sent):
    def transport(draft, *, demo=False):
        assert demo
        sent.append(draft['id'])
        return {'status': 'simulated', 'message_id': draft['id']}
    result = WorkflowServices(email=EmailService(tmp_path/'mail.db', transport=transport))
    result.demo_delay = 0
    return result


def kind(result):
    return result['__interrupt__'][0].value['kind']


async def to_mail_review(graph, config):
    result = await graph.ainvoke({'run_id': config['configurable']['thread_id'], 'user_input': '寻找食品公司工程经理', 'mode': 'demo'}, config)
    assert kind(result) == 'review'
    lead = result['review_leads'][0]
    result = await graph.ainvoke(Command(resume={'action': 'select', 'lead_ids': [lead['id']]}), config)
    assert kind(result) == 'contacts'
    result = await graph.ainvoke(Command(resume={'action': 'confirm_contact', 'lead_id': lead['id'], 'email': 'reviewed@example.com', 'confirmed': True}), config)
    assert kind(result) == 'contacts'
    result = await graph.ainvoke(Command(resume={'action': 'compose', 'brief': {
        'lead_ids': [lead['id']], 'keywords': '设备合作，邀请交流', 'signature': 'Example', 'language': 'en', 'tone': 'friendly',
    }}), config)
    assert kind(result) == 'compose'
    return result


@pytest.mark.asyncio
async def test_nodes_pause_then_edit_and_send_through_graph(tmp_path):
    sent, entered = [], []
    async def observe(name, action):
        entered.append(name)
    graph = create_graph(MemorySaver(), services=services(tmp_path, sent), observer=observe)
    config = {'configurable': {'thread_id': 'direct'}}
    result = await to_mail_review(graph, config)
    assert not sent
    draft = result['drafts'][0]
    result = await graph.ainvoke(Command(resume={'action': 'edit', 'id': draft['id'], 'revision': 1,
                                                'subject': 'Reviewed subject', 'body': 'Reviewed body'}), config)
    assert kind(result) == 'compose'
    assert result['drafts'][0]['revision'] == 2
    assert not sent
    result = await graph.ainvoke(Command(resume={'action': 'send', 'confirmed': True,
                                                'drafts': [{'id': draft['id'], 'revision': 2}]}), config)
    assert result['drafts'][0]['status'] == 'simulated'
    assert not (await graph.aget_state(config)).next
    assert sent == [draft['id']]
    assert {'human_review', 'contact_search', 'contact_review', 'mail_brief', 'mail_write', 'mail_review', 'mail_send'}.issubset(entered)


@pytest.mark.asyncio
async def test_invalid_resume_reinterrupts_without_search_or_send(tmp_path):
    sent = []
    graph = create_graph(MemorySaver(), services=services(tmp_path, sent))
    config = {'configurable': {'thread_id': 'invalid'}}
    result = await graph.ainvoke({'user_input': '寻找工程经理', 'mode': 'demo'}, config)
    result = await graph.ainvoke(Command(resume={'lead_ids': ['not-a-lead']}), config)
    assert kind(result) == 'review'
    assert result['__interrupt__'][0].value['error']
    assert result.get('contacts', {}) == {}
    lead_id = result['review_leads'][0]['id']
    result = await graph.ainvoke(Command(resume={'lead_ids': [lead_id]}), config)
    assert kind(result) == 'contacts'
    assert not sent


@pytest.mark.asyncio
async def test_sqlite_checkpoint_resumes_mail_review_after_new_graph_and_connection(tmp_path):
    sent = []
    config = {'configurable': {'thread_id': 'persistent'}}
    db = str(tmp_path/'checkpoints.db')
    async with AsyncSqliteSaver.from_conn_string(db) as saver:
        graph = create_graph(saver, services=services(tmp_path, sent))
        result = await to_mail_review(graph, config)
        draft_id = result['drafts'][0]['id']
    # 模拟服务重启：新连接、新 graph、新 services，继续同一 thread_id。
    async with AsyncSqliteSaver.from_conn_string(db) as saver:
        graph = create_graph(saver, services=services(tmp_path, sent))
        snapshot = await graph.aget_state(config)
        assert snapshot.next == ('mail_review',)
        result = await graph.ainvoke(Command(resume={'action': 'send', 'confirmed': True,
                                                    'drafts': [{'id': draft_id, 'revision': 1}]}), config)
        assert result['drafts'][0]['status'] == 'simulated'
        assert sent == [draft_id]


@pytest.mark.asyncio
async def test_graph_replay_does_not_repeat_mail_side_effect(tmp_path):
    sent = []
    config = {'configurable': {'thread_id': 'replay'}}
    graph = create_graph(MemorySaver(), services=services(tmp_path, sent))
    result = await to_mail_review(graph, config)
    draft = result['drafts'][0]
    # 保存发送前的检查点，之后显式重放同一确认。
    checkpoint = (await graph.aget_state(config)).config
    approval = {'action': 'send', 'confirmed': True, 'drafts': [{'id': draft['id'], 'revision': 1}]}
    await graph.ainvoke(Command(resume=approval), config)
    await graph.ainvoke(Command(resume=approval), checkpoint)
    assert sent == [draft['id']]


@pytest.mark.asyncio
async def test_mail_service_rejects_changed_content_and_marks_unrecorded_submission_unknown(tmp_path):
    sent = []
    email = services(tmp_path, sent).email
    draft = {'id': 'd', 'revision': 1, 'sender': 's@example.com', 'recipient': 'r@example.com', 'subject': 'Hi', 'body': 'Reviewed'}
    approval = draft_digest(draft)
    with pytest.raises(ValueError, match='不一致'):
        await email.send_once('r', dict(draft, body='Changed'), approval, demo=True)
    db = email._connect()
    db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?)', ('r', 'd', draft['recipient'], approval, json.dumps({'status': 'sending'})))
    db.commit()
    db.close()
    result = await email.send_once('r', draft, approval, demo=True)
    assert result['status'] == 'unknown'
    assert not sent


@pytest.mark.asyncio
async def test_latest_research_flows_into_human_review_and_sqlite_preserves_models(tmp_path):
    settings = Settings()
    provider = DemoSearch()
    bundle = WorkflowServices(settings, SearchService(settings, provider), DemoModel())
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'live.db')) as saver:
        graph = create_graph(saver, services=bundle)
        result = await graph.ainvoke({'user_input': 'fixture', 'mode': 'live'}, {'configurable': {'thread_id': 'live-fixture'}})
        assert kind(result) == 'review'
        assert len(result['review_leads']) == 3
        assert result['review_leads'][0]['name'] == 'Alice Jones'
        assert result['target_profile'].original_request == 'fixture'
