#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_extract.py
@Author ：zlh
@Date ：2026-09-09 13:34 
"""
from backend.graph.states.person_graph_state import PersonSearchWorkerState
from backend.graph.states.person_extract_state import ExtractedLeadCandidateList
from backend.graph.prompts.person_prompts import person_extract_prompt
from backend.graph.llm.deepseek import get_structured_deepseek
from backend.graph.states.person_graph_state import LeadCandidate
from backend.graph.utils.person_utils import clean_candidate
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.error.error_handle import invoke_structured_with_retry


def person_extract(state: PersonSearchWorkerState):
    print("进入person_extract")
    task = state["task"]
    search_results = state["search_results"]
    structured_deepseek = get_structured_deepseek(ExtractedLeadCandidateList)
    message = [
        SystemMessage(
            content=person_extract_prompt
        ),
        HumanMessage(
            content=f"""
            已知信息如下:
            Company:
            {task.company_name}
            
            Target Role:
            {task.target_role}
            
            Searched Role:
            {task.searched_role}
            
            Strategy Type:
            {task.strategy_type}
            
            Objective:
            {task.objective}
            
            Query:
            {task.query}
            
            Expected Signal:
            {task.expected_signal}
            ---------------------------------
            搜索结果:
            {search_results}
            """
        )
    ]
    try:
        response = structured_deepseek.invoke(message)["parsed"]
    except Exception as e:
        # 失败重试
        response = invoke_structured_with_retry(structured_deepseek, ExtractedLeadCandidateList, message)
    result = clean_candidate(response, task)
    print("===============================person_extract处理完毕===============================")
    print(result)
    return {
        "lead_candidates": result
    }