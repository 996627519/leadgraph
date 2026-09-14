#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：lead_gate.py
@Author ：zlh
@Date ：2026-09-12 16:26 
"""
from backend.graph.node.common import stable_id
import logging
logger = logging.getLogger(__name__)

"""
判断哪些需要enrich，哪些信息不足
信息不足判断依据（以下任意条件符合就成立）：
1. 在职状态为former
2. 没有evidence
3. 没有职称
4. 没有公司名
"""
def lead_gate(state, services):
    logger.info("进入lead_gate")
    eligible, skipped = [], []
    for lead in state.get('merged_leads', []):
        reason = ''
        if set(lead.employment_statuses) == {'former'}:
            reason = 'former_only'
        elif not lead.evidence or not lead.titles or not (lead.company_names or lead.target_companies):
            reason = 'insufficient_identity'
        if reason:
            skipped.append({'name': lead.name, 'reason': reason})
        else:
            eligible.append(lead)
    eligible.sort(key=lambda x: (-int(set(x.employment_statuses) == {'current'}), -len({e.url for e in x.evidence}), x.name.casefold(), tuple(sorted(x.company_names))))
    limit = services.settings.max_leads_to_enrich
    skipped.extend({'name': lead.name, 'reason': 'enrichment_limit'} for lead in eligible[limit:])
    eligible = eligible[:limit]
    logger.info("===============================lead_gate处理完毕===============================")
    logger.info(f"selected_leads: {eligible} \nskipped_leads: {skipped}")
    return {'selected_leads': eligible, 'skipped_leads': skipped}
