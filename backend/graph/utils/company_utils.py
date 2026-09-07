#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：company_utils.py
@Author ：zlh
@Date ：2026-09-05 21:13 
"""
from typing import Optional
from urllib.parse import urlparse
import re
from backend.graph.states.company_graph_state import NormalizedCompany, CompanyCandidate, CompanyEvidence, MergedCompany
from backend.graph.states.company_score_state import CompanyScore
from collections import defaultdict
from urllib.parse import (
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode
)

LEGAL_SUFFIXES = {
    "llc",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "ltd",
    "limited",
    "co",
    "company",
    "plc",
}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}




def normalize_company_name(name: str) -> str:
    if not name:
        return ""

    # Unicode 友好的小写
    value = name.casefold().strip()

    # 标点变空格
    value = re.sub(
        r"[^\w\s]",
        " ",
        value
    )

    words = value.split()

    # 只从末尾移除公司法律后缀
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()

    return " ".join(words)


# 用于生成domain字段
def resolve_company_domain(company: CompanyCandidate) -> str | None:
    # website 是优先来源
    website_domain = normalize_domain(
        company.website
    )

    if website_domain:
        return website_domain

    # 没有 website 才考虑已有 domain
    return normalize_domain(
        company.domain
    )


# 网站转换为域名
def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip().lower()

    if not value:
        return None

    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)

    domain = parsed.hostname

    if not domain:
        return None

    if domain.startswith("www."):
        domain = domain[4:]

    return domain

# 用于合并之后去重
def normalize_location(location: str | None) -> str | None:
    if not location:
        return None

    value = location.casefold().strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value or None


# 将companycandidate转换为作比较的NormalizedCompany
def normalize_candidate(company: CompanyCandidate) -> NormalizedCompany:
    return NormalizedCompany(
        original=company,

        normalized_name=
            normalize_company_name(
                company.name
            ),

        normalized_domain=
            resolve_company_domain(
                company
            ),

        normalized_location=
            normalize_location(
                company.location
            ),
    )


# 根据domain分组，用于比较
def get_group_domains(group: list[NormalizedCompany]) -> set[str]:

    return {
        item.normalized_domain
        for item in group
        if item.normalized_domain
    }


# 根据name分组，用于比较
def get_group_names(group: list[NormalizedCompany]) -> set[str]:

    return {
        item.normalized_name
        for item in group
        if item.normalized_name
    }


def find_matching_group(company: NormalizedCompany, groups: list[list[NormalizedCompany]]) -> int | None:

    # 1. 有 domain：优先 domain
    if company.normalized_domain:
        domain_matches = []
        for index, group in enumerate(groups):
            domains = get_group_domains(group)
            if (company.normalized_domain in domains):
                domain_matches.append(index)

        if len(domain_matches) == 1:
            return domain_matches[0]

        # domain 没命中时：
        # 只允许和“还没有 domain”的同名组进行匹配
        name_matches = []

        for index, group in enumerate(groups):
            domains = get_group_domains(group)
            names = get_group_names(group)

            if domains:
                continue

            if (company.normalized_name in names):
                name_matches.append(index)

        if len(name_matches) == 1:
            return name_matches[0]

        return None

    # 2. 当前公司没有 domain
    name_matches = []

    for index, group in enumerate(groups):
        names = get_group_names(group)
        if (company.normalized_name in names):
            name_matches.append(index)

    # 只有唯一匹配时才合并
    if len(name_matches) == 1:
        return name_matches[0]

    # 两个不同 domain 的公司名字都一样
    # → 无法判断
    # → 保持独立
    return None


# 聚合相同公司
def group_company_candidates(companies: list[NormalizedCompany]) -> list[list[NormalizedCompany]]:
    groups: list[list[NormalizedCompany]] = []

    for company in companies:
        group_index = find_matching_group(company, groups)
        if group_index is None:
            groups.append([company])
        else:
            groups[group_index].append(company)
    return groups


# 通用字符串去重
def unique_strings(values: list[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if not value:
            continue

        value = value.strip()
        if not value:
            continue

        key = value.casefold()
        if key in seen:
            continue

        seen.add(key)
        result.append(value)
    return result

# 统一化url
def normalize_evidence_url(url: str) -> str:
    url = url.strip()

    parts = urlsplit(url)

    query_params = [
        (key, value)
        for key, value
        in parse_qsl(
            parts.query,
            keep_blank_values=True
        )
        if key.lower()
        not in TRACKING_PARAMS
    ]

    path = parts.path.rstrip("/")

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        path,
        urlencode(query_params),
        ""  # 去 fragment
    ))


# evidence去重
def deduplicate_evidence(evidences: list[CompanyEvidence]) -> list[CompanyEvidence]:

    result: list[CompanyEvidence] = []

    seen: set[tuple[str, str]] = set()

    for evidence in evidences:

        normalized_url = (
            normalize_evidence_url(
                evidence.url
            )
        )

        normalized_snippet = (
            " ".join(
                evidence.snippet
                .casefold()
                .split()
            )
        )

        key = (normalized_url, normalized_snippet)

        if key in seen:
            continue

        seen.add(key)

        result.append(evidence)

    return result


# 最终公司名选择
def choose_best_name(companies: list[CompanyCandidate]) -> str:
    best = max(
        companies,
        key=lambda c: (
            bool(c.website),
            len(c.name.strip())
        )
    )

    return best.name.strip()

# 选择website
def choose_best_website(companies: list[CompanyCandidate]) -> str | None:
    websites = [
        company.website.strip()
        for company in companies
        if company.website
        and company.website.strip()
    ]

    if not websites:
        return None

    # 越短通常越接近官网根地址
    return min(
        websites,
        key=len
    )

# 合并group
def aggregate_company_group(group: list[NormalizedCompany]) -> MergedCompany:
    companies = [
        item.original
        for item in group
    ]

    # name
    name = choose_best_name(
        companies
    )

    # website
    website = choose_best_website(
        companies
    )

    # domain
    domains = unique_strings([
        item.normalized_domain
        for item in group
    ])

    # 正常情况下同一个 group
    # 最多只有一个真实 domain
    domain = (
        domains[0]
        if len(domains) == 1
        else None
    )

    # location
    locations = unique_strings([
        company.location
        for company in companies
    ])

    # description
    descriptions = unique_strings([
        company.description
        for company in companies
    ])

    # matched_reason
    matched_reasons = unique_strings([
        company.matched_reason
        for company in companies
    ])

    # evidence
    all_evidence = []

    for company in companies:
        all_evidence.extend(
            company.evidence
        )

    evidence = deduplicate_evidence(all_evidence)

    return MergedCompany(
        name=name,
        website=website,
        domain=domain,
        locations=locations,
        descriptions=descriptions,
        matched_reasons=matched_reasons,
        evidence=evidence,
        discovery_count=len(companies)
    )

# 过滤None
def remove_none_companies(candidates: list[CompanyCandidate]) -> list[CompanyCandidate]:
    if not candidates:
        return []
    result: list[CompanyCandidate] = []
    for candidate in candidates:
        if candidate is not None:
            result.append(candidate)
    return result


# 合并公司
def merge_companies(candidates: list[CompanyCandidate]) -> list[MergedCompany]:
    print("开始去重合并公司")
    print(candidates)
    if not candidates:
        return []

    candidates = remove_none_companies(candidates)

    # STEP 1: Normalize
    normalized = [
        normalize_candidate(candidate)
        for candidate in candidates
    ]

    # STEP 2: Deduplicate
    groups = group_company_candidates(
        normalized
    )

    # STEP 3: Aggregate
    merged_companies = [
        aggregate_company_group(group)
        for group in groups
    ]

    return merged_companies


# 计算公司的得分
def calculate_company_score(assessment: CompanyScore) -> int:
    print("进入打分")
    print(assessment)
    score = (
        assessment.industry_fit.score * 0.25
        + assessment.company_type_fit.score * 0.25
        + assessment.geography_fit.score * 0.15
        + assessment.capability_fit.score * 0.25
        + assessment.company_size_fit.score * 0.10
    )

    return round(score)


# 公司的推荐程度
def get_company_recommendation(score: int, hard_constraint_pass: bool, confidence: float) -> str:

    if not hard_constraint_pass:
        return "reject"

    if score >= 80:
        return "high"

    if score >= 60:
        return "medium"

    return "low"