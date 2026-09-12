#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_extract.py
@Author ：zlh
@Date ：2026-09-09 13:34 
"""
from backend.graph.states.person_extract_state import ExtractedLeadCandidateList
from backend.graph.prompts.person_prompts import person_extract_prompt
from backend.graph.node.common import messages
from backend.graph.utils.person_utils import clean_candidate
from backend.graph.utils.evidence import verify_citations, canonical_url
from backend.graph.states.search_result import WorkerError
import logging
logger = logging.getLogger(__name__)


async def person_extract(state, services):
    logger.info("进入person_extract")
    sources = state.get('search_results', [])
    if not sources:
        return {'lead_candidates': []}
    result = await services.model.generate(
        ExtractedLeadCandidateList,
        messages(
            person_extract_prompt,
            task=state['task'],
            search_results=sources
        )
    )
    leads = []
    allowed_urls = {canonical_url(s.url) for s in sources}
    for lead in clean_candidate(result, state['task']):
        evidence = verify_citations(lead.evidence, sources)
        if evidence:
            profile = canonical_url(lead.profile_url)
            leads.append(
                lead.model_copy(
                    update={'evidence': evidence, 'profile_url': profile if profile in allowed_urls else None}
                )
            )
    errors = []
    if result.leads and not leads:
        errors = [WorkerError(stage='person_extract', task_id=state['task'].id,
            error_class='EvidenceValidationError', message='所有人候选人都未通过来源验证')]
    print("===============================person_extract处理完毕===============================")
    print(leads)
    return {'lead_candidates': leads, 'errors': errors}
