#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：enrich_search.py
@Author ：zlh
@Date ：2026-09-09 20:06 
"""
from backend.graph.node.common import worker_error
from backend.graph.utils.evidence import parse_tavily_results, clean_search_results
from backend.service.errors import SearchError, BudgetExhausted
import logging
logger = logging.getLogger(__name__)


async def enrichment_search(state, services):
    logger.info("进入enrichment_search")
    attempt = state.get('search_attempts', 0)
    query = state['search_queries'][attempt]
    try:
        response = await services.search.search(query, run_id=state['run_id'], stage='enrichment')
        results = parse_tavily_results(response)
        logger.info(
            "========================================enrichment_search处理完毕========================================")
        logger.info(results)
        return {
            'search_attempts': attempt + 1,
            'search_results': clean_search_results(state.get('search_results', []) + results)
        }
    except SearchError as exc:
        return {
            'search_attempts': attempt + 1,
            'stop_reason': 'budget_exhausted' if isinstance(exc, BudgetExhausted) else 'search_failed',
            'errors': [worker_error('enrichment_search', state['lead'].name, exc)]
        }
