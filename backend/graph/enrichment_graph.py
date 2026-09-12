#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：enrichment_graph.py
@Author ：zlh
@Date ：2026-09-09 20:35 
"""
from functools import partial
from langgraph.graph import StateGraph, START, END
from backend.graph.states.person_enrichment_state import LeadEnrichmentWorkerState
from backend.graph.node.assess_search_need import assess_search_need
from backend.graph.node.build_enrichment_queries import build_enrichment_queries
from backend.graph.node.enrich_search import enrichment_search
from backend.graph.node.evidence_filter import evidence_filter
from backend.graph.node.enrichment_analyze import person_enrichment
from backend.service.workflow_services import WorkflowServices

def get_enrichment_graph(services=None):
    services = services or WorkflowServices()
    builder = StateGraph(LeadEnrichmentWorkerState)
    builder.add_node('assess_search_need', assess_search_need)
    for name, fn in [
        ('build_enrichment_queries', build_enrichment_queries),
        ('enrichment_search', enrichment_search),
        ('evidence_filter', evidence_filter),
        ('person_enrichment', person_enrichment)
    ]:
        builder.add_node(name, partial(fn, services=services))
    builder.add_edge(START, 'assess_search_need')
    builder.add_conditional_edges('assess_search_need', lambda s: 'build_enrichment_queries' if s['needs_search'] else 'person_enrichment')
    builder.add_conditional_edges('build_enrichment_queries', lambda s: 'enrichment_search' if s.get('search_queries') else 'person_enrichment')
    builder.add_edge('enrichment_search', 'evidence_filter')
    builder.add_conditional_edges('evidence_filter', lambda s: 'enrichment_search' if s['needs_search'] and not s.get('stop_reason') else 'person_enrichment')
    builder.add_edge('person_enrichment', END)
    return builder.compile()
