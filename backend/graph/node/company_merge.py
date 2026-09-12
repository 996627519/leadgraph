#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_merge.py
@Author ：zlh
@Date ：2026-09-05 22:16 
"""
from backend.graph.utils.company_utils import merge_companies
import logging
logger = logging.getLogger(__name__)

def company_merge(state):
    logger.info("进入company_merge")
    result = merge_companies(state.get('company_candidates', []))
    logger.info("========================================company_merge处理完毕========================================")
    logger.info(result)
    return {'merged_company': result}
