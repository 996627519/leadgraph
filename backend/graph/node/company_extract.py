#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_extract.py
@Author ：zlh
@Date ：2026-09-05 16:09 
"""
from backend.graph.states.company_graph_state import CompanySearchWorkerState, CompanyCandidate, CompanyCandidateList
from backend.graph.prompts.company_prompts import company_extract_prompts
from backend.graph.llm.deepseek import get_structured_deepseek
from langchain_core.messages import SystemMessage, HumanMessage


def company_extract(state: CompanySearchWorkerState):
    print("进入company_extract")
    task = state["task"]
    search_results = state["search_results"]
    print(search_results)
    structured_deepseek = get_structured_deepseek(CompanyCandidateList)
    message = [
        SystemMessage(
            content=company_extract_prompts
        ),
        HumanMessage(
            content=f"""
            原始搜索任务:
            {task}
            -------------------------------------------------------
            搜索结果:
            {search_results}
            """
        )
    ]
    result = structured_deepseek.invoke(message)["parsed"]
    if result is None:
        print(f"任务｛task｝提取失败")
        return {"company_candidates": []}
    print("===============================company_extract处理完毕===============================")
    print(result)
    return {
        "company_candidates": result.companies
    }
