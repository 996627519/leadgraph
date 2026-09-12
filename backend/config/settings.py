#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：settings.py
@Author ：zlh
@Date ：2026-09-10 16:15 
"""

from configparser import ConfigParser
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    max_company_searches: int = Field(default=4, ge=0, le=50)
    max_companies: int = Field(default=8, ge=0, le=100)
    max_person_searches_per_company: int = Field(default=2, ge=0, le=10)
    max_leads_to_enrich: int = Field(default=10, ge=0, le=100)
    max_enrichment_searches: int = Field(default=2, ge=0, le=5)
    max_search_calls: int = Field(default=40, ge=0)
    search_concurrency: int = Field(default=4, ge=1, le=32)
    llm_concurrency: int = Field(default=4, ge=1, le=32)
    timeout_seconds: float = Field(default=60, gt=0)
    search_attempts: int = Field(default=2, ge=1, le=4)
    llm_attempts: int = Field(default=2, ge=1, le=4)
    cache_ttl_seconds: float = Field(default=900, ge=0)
    cache_max_entries: int = Field(default=256, ge=1)
    min_company_score: int = Field(default=60, ge=0, le=100)
    min_company_confidence: float = Field(default=.5, ge=0, le=1)
    max_evidence_results: int = Field(default=10, ge=1, le=30)

    @classmethod
    def from_ini(cls, path=None):
        path = Path(path) if path else Path(__file__).with_name('config.ini')
        config = ConfigParser()
        config.read(path, encoding='utf-8')
        values = dict(config.items('pipeline')) if config.has_section('pipeline') else {}
        legacy = {'MAX_COMPANIES': 'max_companies', 'MIN_SCORE': 'min_company_score',
                  'MIN_CONFIDENCE': 'min_company_confidence'}
        for old, new in legacy.items():
            if new not in values and config.has_option('company', old):
                values[new] = config.get('company', old)
        return cls.model_validate(values)
