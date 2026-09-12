#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_graph_state.py
@Author ：zlh
@Date ：2026-09-05 15:41 
"""
from dataclasses import dataclass
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
from backend.graph.states.company_search_task import CompanySearchTask
from backend.graph.states.search_result import SearchResult, WorkerError
from operator import add


class CompanyEvidence(BaseModel):
    title: str
    url: str
    snippet: str

class CompanyCandidate(BaseModel):
    name: str
    website: str | None = None
    location: str | None = None
    domain: str | None = None

    description: str | None = None

    matched_reason: str | None = None

    evidence: list[CompanyEvidence] = Field(default_factory=list)

# 用于格式化后去重使用
@dataclass
class NormalizedCompany:
    original: CompanyCandidate

    normalized_name: str
    normalized_domain: str | None
    normalized_location: str | None

class CompanyCandidateList(BaseModel):
    companies: list[CompanyCandidate] = Field(default_factory=list)


class CompanySearchWorkerState(TypedDict, total=False):
    run_id: str
    errors: Annotated[list[WorkerError], add]
    # 输入
    task: CompanySearchTask

    # company_search输出
    search_results: list[SearchResult]

    # company_extract输出
    company_candidates: Annotated[list[CompanyCandidate], add]


class MergedCompany(BaseModel):
    name: str

    website: str | None = None
    domain: str | None = None

    locations: list[str] = Field(default_factory=list)

    descriptions: list[str] = Field(default_factory=list)

    matched_reasons: list[str] = Field(default_factory=list)

    evidence: list[CompanyEvidence] = Field(default_factory=list)

    discovery_count: int = 1