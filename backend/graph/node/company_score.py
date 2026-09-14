#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_score.py
@Author ：zlh
@Date ：2026-09-07 13:24 
"""
from backend.graph.states.company_score_state import CompanyScore, CompanyScoreAssessment
from backend.graph.prompts.company_prompts import company_score_prompt
from backend.graph.node.common import messages
from backend.graph.utils.company_utils import calculate_company_score, get_company_recommendation
import logging
logger = logging.getLogger(__name__)


async def company_score(state, services):
    logger.info("进入company_score")
    assessment = await services.model.generate(
        CompanyScoreAssessment,
        messages(
            company_score_prompt,
            company=state['company'],
            target_profile=state['target_profile']
        )
    )
    score = calculate_company_score(assessment, state['target_profile'])
    # 如果存在硬性要求且符合才视为合格
    passed = assessment.hard_constraint_pass and not assessment.failed_hard_constraints
    result = CompanyScore(
        **assessment.model_dump(exclude={'hard_constraint_pass'}),
        company=state['company'],
        hard_constraint_pass=passed,
        total_score=score,
        recommendation=get_company_recommendation(score, passed, assessment.confidence))
    logger.info("===============================company_score处理完毕===============================")
    logger.info(result)
    return {'company_score': [result]}
