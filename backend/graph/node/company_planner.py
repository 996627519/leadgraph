#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_planner.py
@Author ：zlh
@Date ：2026-09-05 13:44 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.llm.deepseek import get_structured_deepseek
from backend.graph.states.company_search_task import CompanySearchPlan
from backend.graph.prompts.graph_prompts import company_planner_prompts
from langchain_core.messages import SystemMessage, HumanMessage


def company_planner(state: LeadGraphState):
    print("进入company_planner")
    target_profile = state["target_profile"]
    structured_deepseek = get_structured_deepseek(CompanySearchPlan)
    message =[
        SystemMessage(
            content=company_planner_prompts
        ),
        HumanMessage(
            content=f"""
        经处理过后的target_profile如下:
        {target_profile}
        """
        )
    ]
    result = structured_deepseek.invoke(message)
    print("===============================company_planner处理完毕===============================")
    print(result)
    return {
        "company_search_plan": result
    }




