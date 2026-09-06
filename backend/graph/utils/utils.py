#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：utils.py
@Author ：zlh
@Date ：2026-09-05 21:13 
"""
from typing import Optional
from urllib.parse import urlparse
import re
from backend.graph.states.company_graph_state import NormalizedCompany, CompanyCandidate
from collections import defaultdict

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