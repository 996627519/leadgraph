#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：router.py
@Author ：zlh
@Date ：2026-09-05 20:34 
"""
from collections import defaultdict
from langgraph.types import Send
from backend.graph.utils.person_utils import find_target_company

# 并行company搜索和提取子图，根据target_profile的company_search_plan.tasks
def send_company_work(state):
    if state.get('status') == 'failed':
        return 'finalize'
    tasks = state['company_search_plan'].tasks
    return [Send('company_work', {'task': t, 'run_id': state['run_id']}) for t in tasks] or 'finalize'

# 并行企业打分node，根据company字段分发
def send_company_score(state):
    return [Send('company_score', {'company': c, 'target_profile': state['target_profile']})
            for c in state.get('merged_company', [])] or 'finalize'

# 并行person搜索和提取子图，根据person_search_task.tasks
def send_person_work(state):
    if state.get('status') == 'failed':
        return 'finalize'
    groups = defaultdict(list)
    for task in state['person_search_tasks'].tasks:
        groups[task.company_name].append(task)
    return [Send('person_work', {'tasks': tasks, 'run_id': state['run_id']})
            for _, tasks in sorted(groups.items())] or 'finalize'

# 并行person信息补充，根据selected_leads
def send_person_enrichment(state):
    return [Send('enrichment_work', {'lead': lead, 'target_profile': state['target_profile'],
            'target_company': find_target_company(lead, state), 'run_id': state['run_id']})
            for lead in state.get('selected_leads', [])] or 'finalize'