#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_extract.py
@Author ：zlh
@Date ：2026-09-05 16:09 
"""
from backend.graph.states.company_graph_state import CompanyCandidateList
from backend.graph.prompts.company_prompts import company_extract_prompts
from backend.graph.node.common import messages
from backend.graph.utils.evidence import verify_citations, canonical_url
from backend.graph.states.search_result import WorkerError
import logging
logger = logging.getLogger(__name__)

async def company_extract(state, services):
    logger.info("进入company_extract")
    sources = state.get('search_results', [])
    if not sources:
        return {'company_candidates': []}
    result = await services.model.generate(CompanyCandidateList, messages(company_extract_prompts, task=state['task'], search_results=sources))
    companies = []
    for company in result.companies:
        evidence = verify_citations(company.evidence, sources)
        if not company.name.strip() or not evidence:
            continue
        companies.append(company.model_copy(update={'name': company.name.strip(), 'evidence': evidence, 'website': canonical_url(company.website) or None}))
    errors = []
    if result.companies and not companies:
        errors = [WorkerError(stage='company_extract', task_id=state['task'].id,
            error_class='EvidenceValidationError', message='候选公司来源校验失败')]
    logger.info("========================================company_extract处理完毕========================================")
    logger.info(companies)
    return {'company_candidates': companies, 'errors': errors}