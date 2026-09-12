#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_enrichment_state.py
@Author ：zlh
@Date ：2026-09-09 16:01 
"""
from typing import Literal
from pydantic import BaseModel, Field
from backend.graph.states.person_merge_state import MergedLead
from typing import TypedDict, Annotated

from backend.graph.states.person_graph_state import SearchResult
from backend.graph.states.target_profile import TargetProfile
from backend.graph.states.company_graph_state import MergedCompany
from operator import add
from backend.graph.states.search_result import WorkerError


class EnrichmentEvidence(BaseModel):
    title: str
    url: str
    snippet: str

    evidence_type: Literal[
        "employment",
        "role",
        "company",
        "location",
        "responsibility",
        "project",
        "industry",
        "other",
    ] = "other"


class EnrichedLeadAssessment(BaseModel):

    current_company: str | None = None

    current_title: str | None = None

    current_employment_status: Literal[
        "current",
        "former",
        "unclear"
    ] = "unclear"

    location: str | None = None

    seniority: Literal[
        "executive",
        "director",
        "manager",
        "senior_individual_contributor",
        "individual_contributor",
        "unknown"
    ] = "unknown"

    functional_area: str | None = None

    relevant_responsibilities: list[str] = Field(default_factory=list)

    relevant_projects: list[str] = Field(default_factory=list)

    industry_experience: list[str] = Field(default_factory=list)

    evidence: list[EnrichmentEvidence] = Field(default_factory=list)

    conflicting_information: list[str] = Field(default_factory=list)

    missing_information: list[str] = Field(default_factory=list)

    confidence: float = Field(
        ge=0,
        le=1
    )

    summary: str


class EnrichedLead(EnrichedLeadAssessment):
    lead: MergedLead
    stop_reason: str = ''
    search_attempts: int = 0


class LeadEnrichmentWorkerState(TypedDict, total=False):
    run_id: str
    lead: MergedLead
    target_profile: TargetProfile
    target_company: MergedCompany | None
    search_queries: list[str]
    search_results: list[SearchResult]
    selected_results: list[SearchResult]
    enriched_lead: list[EnrichedLead]
    needs_search: bool
    search_attempts: int
    stop_reason: str
    errors: Annotated[list[WorkerError], add]