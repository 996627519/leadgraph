#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_search.py
@Author ：zlh
@Date ：2026-09-08 16:06 
"""
from backend.graph.utils.evidence import parse_tavily_results
import logging
logger = logging.getLogger(__name__)


async def person_search(state, services):
    logger.info("进入person_planner")
    task = state['task']
    count = {'exact_role_search': 5, 'role_family_search': 8, 'company_team_search': 10, 'project_people_search': 10}.get(task.strategy_type, 5)
    response = await services.search.search(task.query, run_id=state['run_id'], stage='person', max_results=count)
    result = parse_tavily_results(response, task.id)
    print("===============================person_planner处理完毕===============================")
    print(result)
    return {'search_results': result}
