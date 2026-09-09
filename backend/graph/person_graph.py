#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_graph.py
@Author ：zlh
@Date ：2026-09-09 14:32 
"""
from langgraph.graph import StateGraph, START, END
from backend.graph.states.person_graph_state import PersonSearchWorkerState
from backend.graph.node.person_search import person_search
from backend.graph.node.person_extract import person_extract


# 子图，用于根据公司进行人员搜索和信息提取
def get_person_graph():
    person_graph_builder = StateGraph(PersonSearchWorkerState)

    person_graph_builder.add_node(
        "person_search",
        person_search
    )

    person_graph_builder.add_node(
        "person_extract",
        person_extract
    )

    person_graph_builder.add_edge(
        START,
        "person_search"
    )

    person_graph_builder.add_edge(
        "person_search",
        "person_extract"
    )

    person_graph_builder.add_edge(
        "person_extract",
        END
    )

    person_graph = person_graph_builder.compile()
    return person_graph