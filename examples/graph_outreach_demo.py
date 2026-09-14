#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：graph_outreach_demo.py
@Author ：zlh
@Date ：2026-09-14 10:47 
"""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.persistend.checkpoint import open_checkpointer
from langgraph.types import Command
from backend.graph.main_graph import create_graph
from backend.service.workflow_services import WorkflowServices
from backend.service.email_service import EmailService


async def demo():
    with TemporaryDirectory(prefix='leadgraph-demo-') as directory:
        services = WorkflowServices(email=EmailService(Path(directory)/'mail.db'))
        services.demo_delay = 0
        async with open_checkpointer(Path(directory)/'checkpoints.sqlite3') as saver:
            graph = create_graph(saver, services=services)
            config = {'configurable': {'thread_id': 'offline-outreach-demo'}}
            result = await graph.ainvoke({'user_input': '寻找食品加工公司的工程负责人', 'mode': 'demo'}, config)
            lead_id = result['review_leads'][0]['id']
            print('Paused:', result['__interrupt__'][0].value['kind'])
            result = await graph.ainvoke(Command(resume={'action': 'select', 'lead_ids': [lead_id]}), config)
            print('Paused:', result['__interrupt__'][0].value['kind'])
            result = await graph.ainvoke(Command(resume={
                'action': 'confirm_contact', 'lead_id': lead_id, 'email': 'demo@example.com', 'confirmed': True,
            }), config)
            result = await graph.ainvoke(Command(resume={'action': 'compose', 'brief': {
                'lead_ids': [lead_id], 'keywords': '设备升级，邀请简短交流', 'language': 'zh',
                'tone': 'professional', 'signature': 'Example Equipment',
            }}), config)
            print('Paused:', result['__interrupt__'][0].value['kind'])
            draft = result['drafts'][0]
            result = await graph.ainvoke(Command(resume={'action': 'edit', 'id': draft['id'], 'revision': 1,
                                                         'subject': '演示：设备升级交流', 'body': '这是一封经过演示审核的草稿。'}), config)
            result = await graph.ainvoke(Command(resume={'action': 'send', 'confirmed': True,
                                                         'drafts': [{'id': draft['id'], 'revision': 2}]}), config)
            print('Final:', result['drafts'][0]['status'])
            assert result['drafts'][0]['status'] == 'simulated'
            print('No real email was sent.')


if __name__ == '__main__':
    asyncio.run(demo())