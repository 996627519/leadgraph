#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：target_parser_node.py
@Author ：zlh
@Date ：2026-09-04 19:52 
"""
from backend.graph.states.target_profile import TargetProfile
from backend.graph.prompts.company_prompts import target_parser_prompts
from backend.graph.node.common import messages
import logging
logger = logging.getLogger(__name__)


async def target_parser_node(state, services):
    logger.info("进入target_parser_node")
    target = await services.model.generate(TargetProfile, messages(target_parser_prompts, user_input=state['user_input']))
    target = target.model_copy(update={'original_request': state['user_input']})
    if not target.target_roles:
        return {'target_profile': target, 'status': 'needs_input', 'summary': '请补充希望寻找的岗位，例如采购经理、工程经理或生产负责人。'}
    logger.info("========================================target_parser_node处理完毕========================================")
    logger.info(target)
    return {'target_profile': target}
