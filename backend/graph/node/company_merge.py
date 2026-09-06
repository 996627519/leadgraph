#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_merge.py
@Author ：zlh
@Date ：2026-09-05 22:16 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.states.company_graph_state import NormalizedCompany
from backend.graph.utils.utils import normalize_domain, normalize_company_name

def company_merge(state: LeadGraphState):
    print("进入company_merge")
    company_candidates = state["company_candidates"]

