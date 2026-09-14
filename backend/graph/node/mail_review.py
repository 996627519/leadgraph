#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：mail_review.py
@Author ：zlh
@Date ：2026-09-14 10:18 
"""
from backend.graph.node.human_review import wait_for_review
from backend.graph.utils.outreach_validation import validate_mail
import logging
logger = logging.getLogger(__name__)

def mail_review(state):
    logger.info("===============================mail_review处理完毕===============================")
    """编辑与发送都通过 Command(resume=...) 返回图内，不直接修改检查点。"""
    return wait_for_review(state, 'compose', validate_mail)