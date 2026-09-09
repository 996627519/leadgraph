#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_rank.py
@Author ：zlh
@Date ：2026-09-07 19:00 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.utils.company_utils import rank_company


def company_rank(state: LeadGraphState):
    print("进入company_rank")
    company_score = state["company_score"]
    result = rank_company(company_score)
    print("===============================company_rank处理完毕===============================")
    print(result)
    return {
        "ranked_companies": result
    }