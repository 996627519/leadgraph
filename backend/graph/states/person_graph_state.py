#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_graph_state.py
@Author ：zlh
@Date ：2026-09-08 15:52 
"""
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
from typing import Literal
from operator import add

from backend.graph.states.person_search_state import PersonSearchTask


class LeadEvidence(BaseModel):
    title: str
    url: str
    snippet: str

class LeadCandidate(BaseModel):
    # 人员姓名
    name: str
    # 当前搜索结果显示的职位
    title: str | None = None
    # 公司名称
    company_name: str | None = None
    # 人员所在地
    location: str | None = None
    # 公开职业主页，例如 LinkedIn 公开页面、公司 Team 页面等
    profile_url: str | None = None

    # 搜索结果是否明确表明目前仍在该公司
    employment_status: Literal[
        "current",
        "former",
        "unclear"
    ] = "unclear"
    # 为什么这个人值得作为候选 Lead
    matched_reason: str | None = None
    # 支撑这个人员身份/职位/公司关系的证据
    evidence: list[LeadEvidence] = Field(
        default_factory=list
    )

    # 程序补充
    task_id: str | None = None
    target_company: str | None = None
    target_role: str | None = None
    searched_role: str | None = None
    strategy_type: str | None = None


class SearchResult(BaseModel):
    task_id: str | None = None
    title: str
    url: str
    snippet: str
    domain: str | None = None
    provider: str | None = None
    score: float | None = None


class PersonSearchWorkerState(TypedDict):
    task: PersonSearchTask

    search_results: list[SearchResult]

    lead_candidates: Annotated[list[LeadCandidate], add]