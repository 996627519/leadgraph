#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：build_enrichment_queries.py
@Author ：zlh
@Date ：2026-09-09 20:00 
"""
import logging
logger = logging.getLogger(__name__)

def build_enrichment_queries(state, services):
    logger.info("进入build_enrichment_queries")
    lead = state['lead']
    company = state.get('target_company')
    companies = lead.company_names or lead.target_companies
    queries = []
    if company and company.domain:
        queries.append(f'site:{company.domain} "{lead.name}"')
    for name in companies[:2]:
        queries.append(f'"{lead.name}" "{name}"')
    if not queries:
        # 没有充足的信息提供搜索
        return {'search_queries': [], 'stop_reason': 'insufficient_identity'}
    query = list(dict.fromkeys(queries))[:services.settings.max_enrichment_searches]
    logger.info("========================================build_enrichment_queries处理完毕========================================")
    logger.info(query)
    return {'search_queries': query}
