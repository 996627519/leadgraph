#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_search_task.py
@Author ：zlh
@Date ：2026-09-05 13:49 
"""
from pydantic import BaseModel, Field
from typing import Literal


class CompanySearchTask(BaseModel):
    # 搜索任务id
    id: str
    # 搜索策略
    strategy_type: Literal[
        "industry_search",
        "company_type_search",
        "capability_search",
        "directory_search",
        "project_search",
        "mixed_search"
    ]
    # 目标
    objective: str
    # 搜索词
    query: str
    # 优先级
    priority: int = Field(
        ge=1,
        le=5
    )
    # 期望信息
    expected_signal: str

class CompanySearchPlan(BaseModel):
    tasks: list[CompanySearchTask]