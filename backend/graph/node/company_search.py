#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_search.py
@Author ：zlh
@Date ：2026-09-05 14:17 
"""
from backend.graph.utils.evidence import parse_tavily_results
import logging
logger = logging.getLogger(__name__)


async def company_search(state, services):
    logger.info("进入company_search")
    task = state['task']
    response = await services.search.search(task.query, run_id=state['run_id'], stage='company')
    result = parse_tavily_results(response, task.id)
    logger.info("========================================company_search处理完毕========================================")
    logger.info(result)
    return {'search_results': result}

