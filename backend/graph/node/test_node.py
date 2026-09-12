#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_node.py
@Author ：zlh
@Date ：2026-09-09 21:57 
"""
from backend.graph.states.lead_graph_state import LeadGraphState
def test_node(state: LeadGraphState):
    print("********************************************test node********************************************")
    print(state["enriched_leads"])

