#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_planner.py
@Author ：zlh
@Date ：2026-09-08 14:23 
"""
from backend.graph.states.person_search_state import PersonSearchPlan
from backend.graph.prompts.person_prompts import person_planner_prompts
from backend.graph.node.common import messages, stable_id
from backend.graph.utils.company_utils import normalize_company_name
import logging
logger = logging.getLogger(__name__)


async def person_planner(state, services):
    logger.info("进入person_planner")
    companies = [r.scored_company.company for r in state.get('ranked_companies', [])]
    limit = services.settings.max_person_searches_per_company
    if not companies or not limit:
        return {'person_search_tasks': PersonSearchPlan(tasks=[])}
    prompt = person_planner_prompts + '\n每家公司优先一个覆盖主要角色族的查询，最多再提供一个补充查询。程序只在首轮没有找到有证据的现任人员时执行补充查询。'
    plan = await services.model.generate(
        PersonSearchPlan,
        messages(
            prompt,
            target_profile=state['target_profile'],
            companies=companies,
            max_tasks_per_company=limit
        )
    )
    lookup = {normalize_company_name(c.name): c for c in companies}
    seen, counts, tasks = set(), {}, []
    for task in sorted(plan.tasks, key=lambda t: (-t.priority, t.query)):
        name = normalize_company_name(task.company_name)
        query = ' '.join(task.query.split())
        if name not in lookup or not query or (name, query.casefold()) in seen or counts.get(name, 0) >= limit:
            continue
        company = lookup[name]
        counts[name] = counts.get(name, 0) + 1
        seen.add((name, query.casefold()))
        tasks.append(task.model_copy(update={'id': stable_id(name, query), 'query': query, 'company_name': company.name,
            'company_website': company.website, 'company_domain': company.domain}))
    result = PersonSearchPlan(tasks=tasks)
    logger.info("===============================person_planner处理完毕===============================")
    logger.info(result)
    return {'person_search_tasks': result}
