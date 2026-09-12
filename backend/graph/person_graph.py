#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_graph.py
@Author ：zlh
@Date ：2026-09-09 14:32 
"""
from functools import partial
from langgraph.graph import StateGraph, START, END
from backend.graph.states.person_graph_state import PersonSearchWorkerState
from backend.graph.node.person_search import person_search
from backend.graph.node.person_extract import person_extract
from backend.service.workflow_services import WorkflowServices

def get_person_graph(services=None):
    services = services or WorkflowServices()
    builder = StateGraph(PersonSearchWorkerState)
    builder.add_node('person_search', partial(person_search, services=services))
    builder.add_node('person_extract', partial(person_extract, services=services))
    builder.add_edge(START, 'person_search')
    builder.add_edge('person_search', 'person_extract')
    builder.add_edge('person_extract', END)
    return builder.compile()
