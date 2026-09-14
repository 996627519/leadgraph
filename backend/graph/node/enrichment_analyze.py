#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：enrichment_analyze.py
@Author ：zlh
@Date ：2026-09-09 16:15 
"""
from backend.graph.states.person_enrichment_state import EnrichedLeadAssessment, EnrichedLead
from backend.graph.prompts.person_prompts import person_enrichment_prompt
from backend.graph.node.common import messages
from backend.graph.utils.evidence import verify_citations
from backend.graph.states.search_result import WorkerError
import logging
logger = logging.getLogger(__name__)


async def person_enrichment(state, services):
    logger.info("进入person_enrichment")
    sources = list(state['lead'].evidence) + state.get('selected_results', [])
    assessment = await services.model.generate(EnrichedLeadAssessment, messages(person_enrichment_prompt,
        lead=state['lead'], target_profile=state['target_profile'], target_company=state.get('target_company'), search_results=state.get('selected_results', [])))
    evidence = verify_citations(assessment.evidence, sources)
    data = assessment.model_dump()
    errors = []
    if not evidence:
        # 证据不充足，保留原始人物信息，删除没有依据的信息
        data = EnrichedLeadAssessment(
            confidence=0,
            summary='未获得可核验的补充证据。',
            missing_information=['Current identity requires verification']
        ).model_dump()
        errors = [WorkerError(
            stage='enrichment_analyze',
            task_id=state['lead'].name,
            error_class='EvidenceValidationError',
            message='Enrichment has no verifiable source citation'
        )]
    data.update(
        evidence=evidence,
        stop_reason=state.get('stop_reason') or 'attempt_limit',
        search_attempts=state.get('search_attempts', 0)
    )
    logger.info("===============================person_enrichment处理完毕===============================")
    result = [EnrichedLead(lead=state['lead'], **data)]
    logger.info(f"enriched_lead:{result}\nerrors:{errors}")
    return {'enriched_lead': result, 'errors': errors}