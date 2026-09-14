#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：mail_write.py
@Author ：zlh
@Date ：2026-09-14 10:17 
"""
from uuid import uuid5, NAMESPACE_URL
import logging
logger = logging.getLogger(__name__)


async def mail_write(state, services):
    logger.info("进入mail_write")
    leads = [lead for lead in state['review_leads'] if lead['id'] in state['brief']['lead_ids']]
    drafts, notice = await services.outreach.write(
        leads, state['contacts'], state['brief'], demo=state.get('mode') == 'demo', model=services.model)
    for draft in drafts:
        # 同一图任务、同一收件人具有稳定的草稿身份，便于检查点重放防重。
        draft['id'] = uuid5(NAMESPACE_URL, state['run_id'] + ':' + draft['lead_id']).hex
    logger.info("===============================mail_write处理完毕===============================")
    logger.info(drafts)
    return {'drafts': state.get('drafts', []) + drafts, 'notice': notice,
            'outreach_status': 'compose', 'outreach_action': 'review'}
