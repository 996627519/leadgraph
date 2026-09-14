#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：outreach_graph.py
@Author ：zlh
@Date ：2026-09-13 18:07 
"""
from functools import partial
from langgraph.graph import END
from backend.graph.node.mail_skip import mail_skip
from backend.graph.node.prepare_review import prepare_review, demo_research
from backend.graph.node.human_review import human_review
from backend.graph.node.contact_search import contact_search
from backend.graph.node.contact_review import contact_review
from backend.graph.node.mail_brief import mail_brief
from backend.graph.node.mail_write import mail_write
from backend.graph.node.mail_review import mail_review
from backend.graph.node.mail_send import mail_send
from backend.graph.router.router import (
    after_research, after_human_review, after_contact_review,
    after_mail_write, after_mail_review, after_mail_send,
)


def add_outreach_nodes(builder, services, observed=lambda name, fn: fn):
    for name, fn in [
        ('prepare_review', prepare_review),
        ('human_review', human_review),
        ('contact_review', contact_review),
        ('mail_brief', mail_brief),
        ('mail_review', mail_review),
        ('mail_skip', mail_skip),
    ]:
        builder.add_node(name, observed(name, fn))
    for name, fn in [
        ('demo_research', demo_research),
        ('contact_search', contact_search),
        ('mail_write', mail_write),
        ('mail_send', mail_send)
    ]:
        builder.add_node(name, observed(name, partial(fn, services=services)))
    builder.add_conditional_edges('finalize', after_research)
    builder.add_edge('demo_research', 'prepare_review')
    builder.add_edge('prepare_review', 'human_review')
    builder.add_conditional_edges('human_review', after_human_review)
    builder.add_edge('contact_search', 'contact_review')
    builder.add_conditional_edges('contact_review', after_contact_review)
    builder.add_edge('mail_brief', 'mail_write')
    builder.add_conditional_edges('mail_write', after_mail_write)
    builder.add_conditional_edges('mail_review', after_mail_review)
    builder.add_conditional_edges('mail_send', after_mail_send)
    builder.add_edge('mail_skip', END)
