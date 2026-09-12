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

# 判断哪些需要enrich，哪些信息已充足
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
    result = eligible[:limit]
    print("===============================lead_gate处理完毕===============================")
    print(result)
    return {'selected_leads': result, 'skipped_leads': skipped}
