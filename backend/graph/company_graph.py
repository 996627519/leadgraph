#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_graph.py
@Author ：zlh
@Date ：2026-09-05 16:48 
"""
from functools import partial
from langgraph.graph import StateGraph, START, END
from backend.graph.states.company_graph_state import CompanySearchWorkerState
from backend.graph.node.company_search import company_search
from backend.graph.node.company_extract import company_extract
from backend.service.workflow_services import WorkflowServices

def get_company_graph(services=None):
    services = services or WorkflowServices()
    builder = StateGraph(CompanySearchWorkerState)
    builder.add_node('company_search', partial(company_search, services=services))
    builder.add_node('company_extract', partial(company_extract, services=services))
    builder.add_edge(START, 'company_search')
    builder.add_edge('company_search', 'company_extract')
    builder.add_edge('company_extract', END)
    return builder.compile()
