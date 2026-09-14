#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：prepare_review.py
@Author ：zlh
@Date ：2026-09-13 18:08 
"""
from uuid import uuid5, NAMESPACE_URL
from examples.studio_demo import research
import logging
logger = logging.getLogger(__name__)

"""把已有的 EnrichedLead 转换为可序列化的审核资料。"""
def prepare_review(state):
    logger.info("进入prepare_review")
    leads = state.get('review_leads', []) if state.get('mode') == 'demo' else []
    if state.get('mode') != 'demo':
        for index, enriched in enumerate(state.get('results', [])):
            lead = enriched.lead
            leads.append({
                'id': uuid5(NAMESPACE_URL, f"{state['run_id']}:{index}:{lead.name}").hex,
                'name': lead.name,
                'company': enriched.current_company or next(iter(lead.company_names or lead.target_companies), '未知公司'),
                'title': enriched.current_title or next(iter(lead.titles), '职位待确认'),
                'location': enriched.location or next(iter(lead.locations), '地点待确认'),
                'confidence': enriched.confidence, 'employment': enriched.current_employment_status,
                'summary': enriched.summary,
                'evidence': [e.model_dump() for e in (enriched.evidence or lead.evidence)],
                'missing': enriched.missing_information, 'conflicts': enriched.conflicting_information,
            })
    logger.info("===============================prepare_review处理完毕===============================")
    logger.info(leads)
    return {'review_leads': leads, 'approved': [], 'contacts': {}, 'drafts': [],
            'mail_approvals': {}, 'outreach_status': 'review'}


async def demo_research(state, services):
    async def emit(stage, title, detail):
        if services.emit:
            await services.emit(stage, title, detail)
    leads, metrics, status = await research(state['user_input'], demo=True, emit=emit,
                                            delay=getattr(services, 'demo_delay', .65))
    return {'review_leads': leads, 'metrics': metrics, 'status': status}
