#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：mail_send.py
@Author ：zlh
@Date ：2026-09-14 10:19 
"""
from copy import deepcopy
from backend.persistend.studio_store import now
import logging
logger = logging.getLogger(__name__)

async def mail_send(state, services):
    """独立副作用节点；不在 interrupt 所在节点里发送邮件。"""
    logger.info("进入mail_send处理完毕")
    drafts = deepcopy(state['drafts'])
    for draft in drafts:
        approval = state.get('mail_approvals', {}).get(draft['id'])
        if approval and draft['status'] == 'draft':
            result = await services.email.send_once(state['run_id'], draft, approval, demo=state.get('mode') == 'demo')
            draft.update(result, finished_at=now())
            if services.emit:
                await services.emit('send', '邮件提交结果已记录', draft['recipient'])
    logger.info("===============================mail_send处理完毕===============================")
    logger.info(drafts)
    return {'drafts': drafts, 'mail_approvals': {}, 'outreach_status': 'completed'}
