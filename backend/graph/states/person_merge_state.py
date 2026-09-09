#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_merge_state.py
@Author ：zlh
@Date ：2026-09-09 15:04 
"""
from pydantic import BaseModel, Field
from dataclasses import dataclass
from backend.graph.states.person_graph_state import LeadEvidence, LeadCandidate


class MergedLead(BaseModel):
    name: str

    company_names: list[str] = Field(default_factory=list)

    titles: list[str] = Field(default_factory=list)

    locations: list[str] = Field(default_factory=list)

    profile_urls: list[str] = Field(default_factory=list)

    employment_statuses: list[str] = Field(default_factory=list)

    target_companies: list[str] = Field(default_factory=list)

    target_roles: list[str] = Field(default_factory=list)

    searched_roles: list[str] = Field(default_factory=list)

    strategy_types: list[str] = Field(default_factory=list)

    matched_reasons: list[str] = Field(default_factory=list)

    evidence: list[LeadEvidence] = Field(default_factory=list)

    task_ids: list[str] = Field(default_factory=list)

    discovery_count: int = 1





@dataclass
class NormalizedLead:
    original: LeadCandidate

    normalized_name: str
    normalized_company: str
    normalized_profile_url: str | None
    normalized_location: str | None