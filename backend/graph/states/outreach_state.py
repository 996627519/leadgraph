#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：outreach_state.py
@Author ：zlh
@Date ：2026-09-13 18:24 
"""
from typing import TypedDict, Literal
from pydantic import BaseModel, Field


class MailBrief(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=30)
    keywords: str = Field(min_length=3, max_length=3000)
    language: Literal['zh', 'en'] = 'en'
    tone: Literal['professional', 'friendly', 'concise'] = 'professional'
    signature: str = Field(min_length=1, max_length=1000)


class DraftEdit(BaseModel):
    revision: int = Field(ge=1)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=12000)


class SendItem(BaseModel):
    id: str
    revision: int = Field(ge=1)


class SendRequest(BaseModel):
    drafts: list[SendItem] = Field(min_length=1, max_length=30)
    confirmed: Literal[True]


class OutreachState(TypedDict, total=False):
    mode: Literal['demo', 'live']
    review_leads: list[dict]
    approved: list[str]
    contact_ids: list[str]
    contacts: dict[str, dict]
    brief: dict
    drafts: list[dict]
    mail_approvals: dict[str, str]
    outreach_action: str
    outreach_status: str
    notice: str
