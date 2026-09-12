#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_planner.py
@Author ：zlh
@Date ：2026-09-05 13:44 
"""
from backend.graph.states.company_search_task import CompanySearchPlan
from backend.graph.prompts.company_prompts import company_planner_prompts
from backend.graph.node.common import messages, stable_id
import logging
logger = logging.getLogger(__name__)

async def company_planner(state, services):
    logger.info("进入company_planner")
    limit = services.settings.max_company_searches
    if not limit:
        return {'company_search_plan': CompanySearchPlan(tasks=[])}
    plan = await services.model.generate(CompanySearchPlan, messages(company_planner_prompts, target_profile=state['target_profile'], max_tasks=limit))
    seen, tasks = set(), []
    # 清洗排序去重
    for task in sorted(plan.tasks, key=lambda t: (-t.priority, t.query)):
        query = ' '.join(task.query.split())
        if query and query.casefold() not in seen:
            seen.add(query.casefold())
            tasks.append(task.model_copy(update={'id': stable_id('company', query), 'query': query}))
    result = CompanySearchPlan(tasks=tasks[:limit])
    logger.info("========================================company_planner处理完毕========================================")
    logger.info(result)
    return {'company_search_plan': result}




