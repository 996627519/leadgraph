#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：mail_brief.py
@Author ：zlh
@Date ：2026-09-13 18:24 
"""
from backend.graph.states.outreach_state import MailBrief
import logging
logger = logging.getLogger(__name__)

def mail_brief(state):
    logger.info("===============================mail_brief处理完毕===============================")
    #把邮箱审核阶段提交的关键词、语言、语气与署名规范化。
    return {'brief': MailBrief.model_validate(state['brief']).model_dump(), 'outreach_status': 'drafting'}