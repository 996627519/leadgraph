#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_extract_state.py
@Author ：zlh
@Date ：2026-09-09 14:07 
"""
from typing import Literal
from pydantic import BaseModel, Field
from backend.graph.states.person_graph_state import LeadEvidence


class ExtractedLeadCandidate(BaseModel):
    name: str

    title: str | None = None

    company_name: str | None = None

    location: str | None = None

    profile_url: str | None = None

    employment_status: Literal[
        "current",
        "former",
        "unclear"
    ] = "unclear"

    matched_reason: str | None = None

    evidence: list[LeadEvidence] = Field(
        default_factory=list
    )


class ExtractedLeadCandidateList(BaseModel):
    leads: list[ExtractedLeadCandidate] = Field(default_factory=list)