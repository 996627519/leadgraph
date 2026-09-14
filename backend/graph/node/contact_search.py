#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：contact_search.py
@Author ：zlh
@Date ：2026-09-13 18:14 
"""
import logging
logger = logging.getLogger(__name__)

"""用户选择后，搜索这些人的邮箱"""
async def contact_search(state, services):
    logger.info("进入contact_search")
    contacts = dict(state.get('contacts', {}))
    leads = [lead for lead in state['review_leads']
             if lead['id'] in state['contact_ids'] and not contacts.get(lead['id'], {}).get('confirmed')]
    if leads:
        contacts.update(await services.outreach.contacts(leads, demo=state.get('mode') == 'demo'))
    logger.info("===============================contact_search处理完毕===============================")
    logger.info(contacts)
    return {'contacts': contacts, 'outreach_status': 'contacts', 'outreach_action': 'review'}
