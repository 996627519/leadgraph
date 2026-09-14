#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：assess_search_need.py
@Author ：zlh
@Date ：2026-09-10 14:01 
"""
from backend.graph.utils.evidence import evidence_sufficient
import logging
logger = logging.getLogger(__name__)

# 判断证据是否充足，证据不足的需要enrich
def assess_search_need(state):
    logger.info("进入company_extract")
    enough = evidence_sufficient(state['lead'], state['lead'].evidence)
    logger.info("========================================assess_search_need处理完毕========================================")
    logger.info(enough)
    return {
        'needs_search': not enough,
        'search_attempts': 0,
        'search_results': [],
        'selected_results': [],
        'stop_reason': 'existing_evidence_sufficient' if enough else ''
    }
