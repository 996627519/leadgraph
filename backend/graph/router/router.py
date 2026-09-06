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

def send_company_work(state: LeadGraphState):
    return (Send("company_work", {"task": task}) for task in state["company_search_plan"]["tasks"])
