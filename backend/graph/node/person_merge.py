#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_merge.py
@Author ：zlh
@Date ：2026-09-09 15:03 
"""
from backend.graph.utils.person_utils import merge_leads
import logging
logger = logging.getLogger(__name__)


def person_merge(state):
    logger.info("进入person_merge")
    result = merge_leads(state.get('lead_candidates', []))
    print("===============================person_merge处理完毕===============================")
    print(result)
    return {'merged_leads': result}
