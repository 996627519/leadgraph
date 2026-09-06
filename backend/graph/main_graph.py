#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：main_graph.py
@Author ：zlh
@Date ：2026-09-05 16:47 
"""
from langgraph.graph import StateGraph, START, END
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.node.target_parser_node import target_parser_node
from backend.graph.node.company_planner import company_planner
from backend.graph.company_graph import get_company_graph
from backend.graph.router.router import send_company_work

def create_graph(checkpointer):
    # 主图
    builder_main = StateGraph(LeadGraphState)

    builder_main.add_node(
        "target_profile",
        target_parser_node
    )

    builder_main.add_node(
        "company_planner",
        company_planner
    )
    # 公司搜索提取子图
    company_work = get_company_graph()

    builder_main.add_node(
        "company_work",
        company_work
    )

    builder_main.add_edge(
        START,
        "target_profile"
    )

    builder_main.add_edge(
        "target_profile",
        "company_planner"
    )

    builder_main.add_conditional_edges(
        "target_profile",
        send_company_work
    )




