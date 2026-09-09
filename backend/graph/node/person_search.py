#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_search.py
@Author ：zlh
@Date ：2026-09-08 16:06 
"""
from backend.service.search_service import tavily_search
from backend.graph.states.person_graph_state import PersonSearchWorkerState
from states.company_graph_state import SearchResult
from backend.graph.utils.person_utils import clean_search_results, parse_tavily_results


async def person_search(state: PersonSearchWorkerState):
    print("进入person_search")
    task = state["task"]
    max_results_map = {
        "exact_role_search": 5,
        "role_family_search": 8,
        "company_team_search": 10,
        "project_people_search": 10
    }

    max_results = max_results_map.get(
        task.strategy_type,
        5
    )
    results = await tavily_search(
        query=task.query,
        max_results=max_results,
        search_depth="advanced"
    )

    results = parse_tavily_results(results)
    results = clean_search_results(results)
    print("===============================person_search处理完毕===============================")
    print(results)
    return {
        "search_results": results
    }