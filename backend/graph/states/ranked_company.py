#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：ranked_company.py
@Author ：zlh
@Date ：2026-09-07 19:09 
"""
from pydantic import BaseModel
from backend.graph.states.company_score_state import CompanyScore


class RankedCompany(BaseModel):

    rank: int

    scored_company: CompanyScore