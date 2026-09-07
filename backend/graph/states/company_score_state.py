#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_score_state.py
@Author ：zlh
@Date ：2026-09-07 13:14 
"""
from typing import Literal, TypedDict
from pydantic import BaseModel, Field

from backend.graph.states.company_graph_state import MergedCompany
from backend.graph.states.target_profile import TargetProfile

class CompanyScoreState(TypedDict):
    target_profile: TargetProfile
    company: MergedCompany

class ScoreDimension(BaseModel):
    score: int = Field(ge=0, le=100)

    matched: bool | None = None

    reason: str

    evidence: list[str] = Field(default_factory=list)

class CompanyScore(BaseModel):
    company: MergedCompany

    industry_fit: ScoreDimension
    company_type_fit: ScoreDimension
    geography_fit: ScoreDimension
    capability_fit: ScoreDimension
    company_size_fit: ScoreDimension

    hard_constraint_pass: bool

    failed_hard_constraints: list[str] = Field(default_factory=list)

    missing_information: list[str] = Field(default_factory=list)

    total_score: int = Field(ge=0, le=100)

    confidence: float = Field(ge=0, le=1)

    recommendation: Literal[
        "high",
        "medium",
        "low",
        "reject"
    ]

    summary: str