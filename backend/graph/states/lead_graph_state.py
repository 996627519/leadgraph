#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：lead_graph_state.py
@Author ：zlh
@Date ：2026-09-04 19:48 
"""
from typing import TypedDict, Annotated
from backend.graph.states.target_profile import TargetProfile
from backend.graph.states.company_search_task import CompanySearchPlan
from backend.graph.states.company_graph_state import CompanyCandidate
from backend.graph.states.merged_company import MergedCompany
from backend.graph.states.company_score_state import CompanyScore
from backend.graph.states.person_graph_state import LeadCandidate
from operator import add

from backend.graph.states.ranked_company import RankedCompany
from backend.graph.states.person_search_state import PersonSearchTask
from backend.graph.states.person_merge_state import MergedLead


class LeadGraphState(TypedDict):
    # 用户输入
    user_input: str
    # 目标解析内容
    target_profile: TargetProfile
    # 公司搜索任务
    company_search_plan: CompanySearchPlan
    # 提取后的公司信息
    company_candidates: Annotated[list[CompanyCandidate], add]
    # 去重后的公司
    merged_company: list[MergedCompany]
    # 各公司评分
    company_score: Annotated[list[CompanyScore], add]
    # 公司契合度排名
    ranked_companies: list[RankedCompany]
    # 人员搜索人物
    person_search_tasks: list[PersonSearchTask]
    # 提取后的人员信息
    lead_candidates: Annotated[list[LeadCandidate], add]
    # 去重后的候选人信息
    merged_leads: list[MergedLead]