#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_rank.py
@Author ：zlh
@Date ：2026-09-07 19:00 
"""
from backend.graph.utils.company_utils import rank_company
import logging
logger = logging.getLogger(__name__)


def company_rank(state, services):
    logger.info("进入company_score")
    settings = services.settings
    result = rank_company(
        state.get('company_score', []),
        settings.max_companies,
        settings.min_company_score,
        settings.min_company_confidence
    )
    print("===============================company_rank处理完毕===============================")
    print(result)
    return {'ranked_companies': result}
