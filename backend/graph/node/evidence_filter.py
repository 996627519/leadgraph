#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：evidence_filter.py
@Author ：zlh
@Date ：2026-09-09 20:11 
"""
from backend.graph.utils.evidence import select_evidence, evidence_sufficient
import logging
logger = logging.getLogger(__name__)


def evidence_filter(state, services):
    logger.info("进入evidence_filter")
    # 挑选出最佳evidence
    selected = select_evidence(state['lead'], state.get('search_results', []), services.settings.max_evidence_results)
    # 判断evidence是否充足
    enough = evidence_sufficient(state['lead'], list(state['lead'].evidence) + selected)
    stop = state.get('stop_reason', '')
    if not stop and enough:
        stop = 'evidence_sufficient'
    if not stop and state.get('search_attempts', 0) >= len(state.get('search_queries', [])):
        stop = 'attempt_limit'
    print("===============================evidence_filter处理完毕===============================")
    print(f"selected:{selected}\nneeds_search:{not enough}\nstop_reason:{stop}")
    return {'selected_results': selected, 'needs_search': not enough, 'stop_reason': stop}
