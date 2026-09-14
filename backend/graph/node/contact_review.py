#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：contact_review.py
@Author ：zlh
@Date ：2026-09-13 18:23 
"""
from backend.graph.node.human_review import wait_for_review
from backend.graph.utils.outreach_validation import validate_contact
import logging
logger = logging.getLogger(__name__)


def contact_review(state):
    logger.info("进入contact_review")
    return wait_for_review(state, 'contacts', validate_contact)
