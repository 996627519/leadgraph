#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_utils.py
@Author ：zlh
@Date ：2026-09-05 21:13 
"""
import re
from urllib.parse import urlsplit
from backend.config.settings import Settings
from backend.graph.states.company_graph_state import NormalizedCompany, MergedCompany
from backend.graph.states.ranked_company import RankedCompany
from backend.graph.utils.evidence import canonical_url, unique_strings, normalize_location

LEGAL_SUFFIXES = {'llc', 'inc', 'incorporated', 'corp', 'corporation', 'ltd', 'limited', 'co', 'company', 'plc'}

# 标准化公司名称
def normalize_company_name(name):
    words = re.sub(r'[^\w\s]', ' ', (name or '').casefold()).split()
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return ' '.join(words)

def normalize_domain(value):
    if not value or not value.strip():
        return None
    value = value.strip()
    url = canonical_url(value if '://' in value else 'https://' + value)
    return urlsplit(url).hostname.removeprefix('www.') if url else None

def resolve_company_domain(company):
    return normalize_domain(company.website) or normalize_domain(company.domain)

def normalize_evidence_url(url):
    return canonical_url(url)

# 规范化company字段
def normalize_candidate(company):
    return NormalizedCompany(original=company, normalized_name=normalize_company_name(company.name),
        normalized_domain=resolve_company_domain(company), normalized_location=normalize_location(company.location))

def get_group_domains(group):
    return {x.normalized_domain for x in group if x.normalized_domain}

def get_group_names(group):
    return {x.normalized_name for x in group if x.normalized_name}

def find_matching_group(company, groups):
    if company.normalized_domain:
        matches = [i for i, g in enumerate(groups) if company.normalized_domain in get_group_domains(g)]
        if len(matches) == 1:
            return matches[0]
        matches = [i for i, g in enumerate(groups) if not get_group_domains(g) and company.normalized_name in get_group_names(g)]
    else:
        matches = [i for i, g in enumerate(groups) if company.normalized_name in get_group_names(g)]
    return matches[0] if len(matches) == 1 else None

# 同一家公司合并
def group_company_candidates(companies):
    groups = []
    for company in sorted(companies, key=lambda x: (not bool(x.normalized_domain), x.normalized_domain or '', x.normalized_name)):
        index = find_matching_group(company, groups)
        if index is None:
            groups.append([company])
        else:
            groups[index].append(company)
    return groups

def deduplicate_evidence(evidences):
    result, seen = [], set()
    for item in evidences:
        key = (canonical_url(item.url), ' '.join(item.snippet.casefold().split()))
        if key[0] and key not in seen:
            seen.add(key)
            result.append(item)
    return result

def choose_best_name(companies):
    return max(companies, key=lambda c: (bool(c.website), len(c.name.strip()), c.name)).name.strip()

def choose_best_website(companies):
    websites = [canonical_url(c.website) for c in companies if canonical_url(c.website)]
    return min(websites, key=lambda url: (len(url), url)) if websites else None

# 将一组company合并为一组
def aggregate_company_group(group):
    companies = [x.original for x in group]
    domains = sorted(get_group_domains(group))
    return MergedCompany(name=choose_best_name(companies), website=choose_best_website(companies),
        domain=domains[0] if len(domains)==1 else None,
        locations=unique_strings([c.location for c in companies]),
        descriptions=unique_strings([c.description for c in companies]),
        matched_reasons=unique_strings([c.matched_reason for c in companies]),
        evidence=deduplicate_evidence([e for c in companies for e in c.evidence]), discovery_count=len(companies))

# 去除none/空字符
def remove_none_companies(candidates):
    return [c for c in candidates or [] if c is not None and c.name.strip()]

# 合并公司
def merge_companies(candidates):
    normalized = [normalize_candidate(c) for c in remove_none_companies(candidates)]
    return [aggregate_company_group(g) for g in group_company_candidates(normalized)]

# 公司打分
def calculate_company_score(assessment, target_profile=None):
    dimensions = [
        ('industry_fit', .25, 'industries'),
        ('company_type_fit', .25, 'company_types'),
        ('geography_fit', .15, 'countries'),
        ('capability_fit', .25, 'keywords'),
        ('company_size_fit', .10, 'company_size_min')
    ]
    active = []
    for field, weight, requirement in dimensions:
        enabled = target_profile is None or bool(getattr(target_profile, requirement))
        if target_profile is not None and field == 'geography_fit':
            enabled = bool(target_profile.countries or target_profile.regions)
        if target_profile is not None and field == 'company_size_fit':
            enabled = target_profile.company_size_min is not None or target_profile.company_size_max is not None
        if enabled:
            active.append((getattr(assessment, field).score, weight))
    return round(sum(score * weight for score, weight in active) / sum(w for _, w in active)) if active else 0

def get_company_recommendation(score, hard_constraint_pass, confidence):
    if not hard_constraint_pass:
        return 'reject'
    if confidence < .5:
        return 'low'
    return 'high' if score >= 80 else 'medium' if score >= 60 else 'low'

# 公司符合度排名
def rank_company(scored_companies, max_companies=None, min_score=60, min_confidence=.5):
    if max_companies is None:
        max_companies = Settings.from_ini().max_companies
    eligible = [x for x in scored_companies if x.hard_constraint_pass and x.total_score >= min_score and x.confidence >= min_confidence]
    selected = sorted(eligible, key=lambda x: (-x.total_score, -x.confidence, x.company.domain or '', x.company.name.casefold()))[:max_companies]
    return [RankedCompany(rank=i, scored_company=c) for i, c in enumerate(selected, 1)]
