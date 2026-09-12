#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：router.py
@Author ：zlh
@Date ：2026-09-05 20:34 
"""
from langgraph.types import Send
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.states.person_enrichment_state import LeadEnrichmentWorkerState
from backend.graph.utils.person_utils import find_target_company


# 分发公司搜索和公司信息提取
def send_company_work(state: LeadGraphState):
    return [Send("company_work", {"task": task}) for task in state["company_search_plan"].tasks]

# 分发公司打分node
def send_company_score(state: LeadGraphState):
    return [
        Send(
            "company_score",
            {"target_profile": state["target_profile"], "company": company}
        )
        for company in state["merged_company"]
    ]


# 分发根据公司搜索和提取人员信息
def send_person_work(state: LeadGraphState):
    return [Send("person_work", {"task": task}) for task in state["person_search_tasks"].tasks]

# 分发合并后的候选人给enrich
def send_person_enrichment(state: LeadGraphState):
    return [Send(
            "enrichment_work",
            {
                "lead": lead,
                "target_profile": state["target_profile"],
                "target_company": find_target_company(lead, state)
            }
        )
        for lead
        in state["merged_leads"]]

# 分发enrich搜索任务
def send_enrichment_search(state: LeadEnrichmentWorkerState):
    return [Send("enrichment_search", {"search_query": search_query}) for search_query in state["search_queries"]]


def route_search_need(state: LeadEnrichmentWorkerState):
    if state["needs_search"]:
        return "build_query"

    return "enrichment_analyze"