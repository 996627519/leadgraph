#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_merge.py
@Author ：zlh
@Date ：2026-09-09 15:03 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.utils.person_utils import merge_leads


def person_merge(state: LeadGraphState):
    print("进入person_merge")
    lead_candidates = state["lead_candidates"]
    merged_leads = merge_leads(lead_candidates)
    print("===============================person_merge处理完毕===============================")
    print(merged_leads)
    return {
        "merged_leads":merged_leads
    }