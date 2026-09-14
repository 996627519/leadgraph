#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_utils.py
@Author ：zlh
@Date ：2026-09-08 21:16 
"""
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from backend.graph.states.person_graph_state import LeadCandidate
from backend.graph.states.person_merge_state import NormalizedLead, MergedLead
from backend.graph.utils.company_utils import normalize_company_name, deduplicate_evidence
from backend.graph.utils.evidence import (canonical_url, unique_strings, normalize_location,
    clean_search_results, parse_tavily_results)

def get_domain(url):
    value = canonical_url(url)
    return urlsplit(value).hostname if value else None

def clean_candidate(lead_candidate, task):
    if lead_candidate is None:
        return []
    return [LeadCandidate(**lead.model_dump(), task_id=task.id, target_company=task.company_name,
        target_role=task.target_role, searched_role=task.searched_role, strategy_type=task.strategy_type)
        for lead in lead_candidate.leads if lead and lead.name.strip()]

def normalize_person_name(name):
    value = unicodedata.normalize('NFKC', name or '').casefold()
    return ' '.join(re.sub(r'[^\w\s]', ' ', value).split())

def normalize_profile_url(url):
    if not url:
        return None
    url = canonical_url(url if '://' in url else 'https://' + url)
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit(('https', parts.netloc.removeprefix('www.'), parts.path, parts.query, ''))

# 规范化候选人信息
def normalize_lead_candidate(lead):
    return NormalizedLead(
        original=lead,
        normalized_name=normalize_person_name(lead.name),
        normalized_company=normalize_company_name(lead.company_name),
        normalized_profile_url=normalize_profile_url(lead.profile_url),
        normalized_location=normalize_location(lead.location)
    )

"""
姓名不同 →不同的人
公司非空且不同 →不同的人
URL相同且是个人主页 → 同一人
URL不同且都是LinkedIn个人主页 → 不同人
最终，公司不同则视为不同
"""
def is_same_lead(a, b):
    if not a.normalized_name or a.normalized_name != b.normalized_name:
        return False
    if a.normalized_company and b.normalized_company and a.normalized_company != b.normalized_company:
        return False
    ua, ub = a.normalized_profile_url, b.normalized_profile_url
    if ua and ub and ua == ub:
        parts = urlsplit(ua)
        personal = parts.hostname == 'linkedin.com' and parts.path.startswith('/in/')
        personal = personal or len(a.normalized_name.split()) > 1 and all(part in parts.path.casefold() for part in a.normalized_name.split())
        if personal:
            return True
    if ua and ub and ua != ub and 'linkedin.com/in/' in ua and 'linkedin.com/in/' in ub:
        return False
    return bool(a.normalized_company and a.normalized_company == b.normalized_company)


# 寻找匹配的人
def find_matching_lead_group(lead, groups):
    matches = [i for i, group in enumerate(groups) if all(is_same_lead(lead, other) for other in group)]
    return matches[0] if len(matches)==1 else None

# 匹配的人放在同一组
def group_lead_candidates(leads):
    groups=[]
    for lead in sorted(leads, key=lambda x: (x.normalized_name, x.normalized_company, x.normalized_profile_url or '')):
        index=find_matching_lead_group(lead,groups)
        if index is None:
            groups.append([lead])
        else:
            groups[index].append(lead)
    return groups

def deduplicate_lead_evidence(evidences):
    return deduplicate_evidence(evidences)

# 选择最合适的名字
def choose_best_lead_name(leads):
    return sorted(leads, key=lambda x: (not bool(x.profile_url), x.name))[0].name.strip()

# 汇总候选人(相同的人物信息只选择最佳的那个)
def aggregate_lead_group(group):
    leads=[x.original for x in group]
    mapping={'company_names':'company_name',
             'titles':'title',
             'locations':'location',
             'employment_statuses':'employment_status',
             'target_companies':'target_company',
             'target_roles':'target_role',
             'searched_roles':'searched_role',
             'strategy_types':'strategy_type',
             'matched_reasons':'matched_reason',
             'task_ids':'task_id'}
    data={output:unique_strings([getattr(lead,field) for lead in leads]) for output,field in mapping.items()}
    return MergedLead(name=choose_best_lead_name(leads), **data,
        profile_urls=unique_strings([normalize_profile_url(x.profile_url) for x in leads]),
        evidence=deduplicate_lead_evidence([e for lead in leads for e in lead.evidence]), discovery_count=len(leads))

# 合并候选人信息
def merge_leads(candidates):
    normalized=[normalize_lead_candidate(lead) for lead in candidates or [] if lead and lead.name.strip()]
    return [aggregate_lead_group(group) for group in group_lead_candidates(normalized)]

# 根据候选人寻找目标公司
def find_target_company(lead, state):
    names={normalize_company_name(x) for x in lead.target_companies}
    matches=[r.scored_company.company for r in state.get('ranked_companies', [])
             if normalize_company_name(r.scored_company.company.name) in names]
    return matches[0] if len(matches)==1 else None
