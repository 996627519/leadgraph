#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：merged_company.py
@Author ：zlh
@Date ：2026-09-05 20:56 
"""
from pydantic import BaseModel, Field
from backend.graph.states.company_graph_state import CompanyEvidence


class MergedCompany(BaseModel):
    company_id: str
    name: str
    website: str | None = None
    domain: str | None = None
    locations: list[str] = Field(
        default_factory=list
    )

    descriptions: list[str] = Field(
        default_factory=list
    )

    matched_reasons: list[str] = Field(
        default_factory=list
    )

    matched_task_ids: list[str] = Field(
        default_factory=list
    )

    matched_strategies: list[str] = Field(
        default_factory=list
    )

    evidence: list[CompanyEvidence] = Field(
        default_factory=list
    )

    discovery_count: int = 1