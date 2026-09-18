#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：human_review.py
@Author ：zlh
@Date ：2026-09-13 18:12 
"""
from langgraph.types import interrupt
from backend.graph.utils.outreach_validation import validate_review
import logging
logger = logging.getLogger(__name__)


"""用户选择。interrupt 前端只构造展示数据，不执行搜索或发送。"""
def wait_for_review(state, kind, validate):
    error = ''
    while True:
        answer = interrupt({'kind': kind, 'error': error,
                            'leads': state.get('review_leads', []),
                            'contacts': state.get('contacts', {}),
                            'drafts': state.get('drafts', [])})
        try:
            if not isinstance(answer, dict):
                raise ValueError('请提交结构化的审核内容。')
            return validate(state, answer)
        except ValueError as exc:
            error = str(exc)


def human_review(state):
    logger.info("human_review")
    return wait_for_review(state, 'review', validate_review)
