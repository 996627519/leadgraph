#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph
@File ：mail_send.py
@Author ：zlh
@Date ：2026-09-14 10:19
用户决定不发送，关闭剩余草稿并结束图；不会调用任何邮件服务。
"""
from copy import deepcopy
from backend.persistend.studio_store import now
import logging
logger = logging.getLogger(__name__)


def mail_skip(state):
    logger.info("进入mail_skip")
    drafts = deepcopy(state.get('drafts', []))
    for draft in drafts:
        if draft['status'] == 'draft':
            draft.update(status='skipped', finished_at=now())
    logger.info("===============================mail_skip处理完毕===============================")
    logger.info(drafts)
    return {'drafts': drafts, 'mail_approvals': {}, 'outreach_status': 'skipped',
            'notice': '已结束流程，剩余草稿未发送。'}
