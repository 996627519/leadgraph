#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_graph.py
@Author ：zlh
@Date ：2026-09-05 16:48 
"""
from langgraph.graph import StateGraph, START, END
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.states.company_graph_state import CompanySearchWorkerState
from backend.graph.node.target_parser_node import target_parser_node
from backend.graph.node.company_planner import company_planner
from backend.graph.node.company_search import company_search
from backend.graph.node.company_extract import company_extract

def get_company_graph():
    # 子图，用于并行公司搜索和公司信息提取
    builder_company = StateGraph(CompanySearchWorkerState)

    builder_company.add_node(
        "company_search",
        company_search
    )
    builder_company.add_node(
        "company_extract",
        company_extract
    )

    builder_company.add_edge(
        START,
        "company_search"
    )

    builder_company.add_edge(
        "company_search",
        "company_extract"
    )

    builder_company.add_edge(
        "company_extract",
        END
    )
    company_graph = builder_company.compile()
    return company_graph