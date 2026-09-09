#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_search_state.py
@Author ：zlh
@Date ：2026-09-08 14:30 
"""
from pydantic import BaseModel, Field
from typing import Literal

class PersonSearchTask(BaseModel):
    id: str

    company_name: str
    company_website: str | None = None
    company_domain: str | None = None

    # 真正想找的角色
    target_role: str

    # 当前 query 实际使用的职位名称
    searched_role: str

    strategy_type: Literal[
        "exact_role_search",
        "role_family_search",
        "company_team_search",
        "project_people_search"
    ]

    objective: str

    query: str

    priority: int = Field(
        ge=1,
        le=5
    )

    expected_signal: str


class PersonSearchPlan(BaseModel):
    tasks: list[PersonSearchTask] = Field(default_factory=list)