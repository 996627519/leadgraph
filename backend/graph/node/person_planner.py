#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_planner.py
@Author ：zlh
@Date ：2026-09-08 14:23 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.states.person_search_state import PersonSearchPlan
from backend.graph.llm.deepseek import get_structured_deepseek
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.prompts.person_prompts import person_planner_prompts
from backend.graph.error.error_handle import invoke_structured_with_retry


def person_planner(state: LeadGraphState):
    print("进入person_planner")
    target_profile = state["target_profile"]
    ranked_companies = state["ranked_companies"]
    structured_deepseek = get_structured_deepseek(PersonSearchPlan)
    message = [
        SystemMessage(
            content=person_planner_prompts
        ),
        HumanMessage(
            content=f"""
            Target Profile:
            {target_profile}
            
            Ranked Companies:
            {ranked_companies}
            请生成 person search plan.
            """
        )
    ]
    try:
        response = structured_deepseek.invoke(message)["parsed"]
    except Exception as e:
        # 失败重试
        response = invoke_structured_with_retry(structured_deepseek, PersonSearchPlan, message)
    print("===============================person_planner处理完毕===============================")
    print(response)
    return {
        "person_search_tasks": response
    }