#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：target_profile.py
@Author ：zlh
@Date ：2026-09-05 13:29 
"""
from pydantic import BaseModel, Field


class TargetProfile(BaseModel):
    # 指定国家
    countries: list[str] = Field(default_factory=list)
    # 指定地区
    regions: list[str] = Field(default_factory=list)
    # 企业
    industries: list[str] = Field(default_factory=list)
    # 企业类型
    company_types: list[str] = Field(default_factory=list)
    # 企业规模最小值
    company_size_min: int | None = None
    # 企业规模最大值
    company_size_max: int | None = None
    # 目标客户的角色（岗位）
    target_roles: list[str] = Field(default_factory=list)
    # 关键词
    keywords: list[str] = Field(default_factory=list)
    # 排除的企业
    exclude_companies: list[str] = Field(default_factory=list)
    # 排除的角色
    exclude_roles: list[str] = Field(default_factory=list)
    # 排除的地区
    exclude_regions: list[str] = Field(default_factory=list)
    # 硬性要求
    hard_constraints: list[str] = Field(default_factory=list)
    # 软性要求
    soft_preferences: list[str] = Field(default_factory=list)
    # 原始输入
    original_request: str