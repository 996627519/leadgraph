#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_search.py
@Author ：zlh
@Date ：2026-09-05 14:17 
"""
from backend.service.search_service import tavily_search
from backend.graph.states.company_graph_state import CompanySearchWorkerState
from states.company_graph_state import SearchResult


async def company_search(state: CompanySearchWorkerState):
    print("进入company_search")
    task = state["task"]
    response = await tavily_search(task["query"])
    results = []
    for item in response.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily"
            )
        )
    print("===============================company_search处理完毕===============================")
    return {
        "search_results": results
    }

