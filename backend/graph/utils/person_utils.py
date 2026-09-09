#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：person_utils.py
@Author ：zlh
@Date ：2026-09-08 21:16 
"""
from backend.graph.states.person_graph_state import SearchResult, LeadCandidate, PersonSearchTask
from backend.graph.utils.company_utils import normalize_evidence_url, normalize_company_name
from backend.graph.utils.company_utils import normalize_domain
from backend.graph.states.person_extract_state import ExtractedLeadCandidateList
from backend.graph.states.person_graph_state import LeadEvidence
from urllib.parse import urlparse
import re
import unicodedata
from urllib.parse import (
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode,
)

from backend.graph.states.person_merge_state import NormalizedLead, MergedLead

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}

# 过滤重复 URL、空结果、无内容结果
def clean_search_results(results: list[SearchResult]) -> list[SearchResult]:
    cleaned = []
    seen_urls = set()
    for result in results:
        if not result.url:
            continue
        normalized_url = normalize_evidence_url(result.url)

        if normalized_url in seen_urls:
            continue

        if not result.title and not result.snippet:
            continue

        seen_urls.add(normalized_url)
        cleaned.append(result)

    return cleaned


def get_domain(url: str) -> str | None:
    if not url:
        return None

    return urlparse(url).netloc


# 将搜索结果转换为指定类型
def parse_tavily_results(response: dict) -> list[SearchResult]:
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
            domain=get_domain(
                item.get("url", "")
            ),
            provider="tavily",
            score=item.get("score")
        )
        for item in response.get("results", [])
    ]

# 过滤候选人信息
def clean_candidate(lead_candidate: ExtractedLeadCandidateList, task:PersonSearchTask) -> list[LeadCandidate]:
    if lead_candidate is None:
        return []
    candidates: list[LeadCandidate] = []
    for lead in lead_candidate.leads:
        if lead is None:
            continue
        # 姓名是 LeadCandidate 最基本条件
        if not lead.name or not lead.name.strip():
            continue

        candidate = LeadCandidate(
            **lead.model_dump(),

            task_id=task.id,

            target_company=
                task.company_name,

            target_role=
                task.target_role,

            searched_role=
                task.searched_role,

            strategy_type=
                task.strategy_type
        )

        candidates.append(candidate)
    return candidates


# 标准化人名
def normalize_person_name(name: str | None) -> str:
    if not name:
        return ""

    value = unicodedata.normalize(
        "NFKC",
        name
    )

    value = value.casefold().strip()

    # 标点换为空格
    value = re.sub(
        r"[^\w\s]",
        " ",
        value
    )

    # 多余空格
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()

# 标准化url
def normalize_profile_url(url: str | None) -> str | None:
    if not url:
        return None

    value = url.strip()

    if not value:
        return None

    if "://" not in value:
        value = "https://" + value

    parts = urlsplit(value)

    host = parts.netloc.casefold()

    if host.startswith("www."):
        host = host[4:]

    path = parts.path.rstrip("/")

    query_params = [
        (key, val)
        for key, val in parse_qsl(
            parts.query,
            keep_blank_values=True
        )
        if key.casefold()
        not in TRACKING_PARAMS
    ]

    return urlunsplit((
        "https",
        host,
        path,
        urlencode(query_params),
        ""
    ))


# 轻量化location
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


# 格式化
def normalize_lead_candidate(lead: LeadCandidate) -> NormalizedLead:

    return NormalizedLead(
        original=lead,
        normalized_name = normalize_person_name(lead.name),
        normalized_company = normalize_company_name(lead.company_name),
        normalized_profile_url = normalize_profile_url(lead.profile_url),
        normalized_location = normalize_location(lead.location),
    )

# person去重规则
"""
1
profile_url 相同
→ 高置信同一个人

2
name 完全相同
+
company_name 完全相同
→ 高概率同一个人

3
name 相同
+
target_company 相同
+
实际 company 缺失
→ 可以有限度合并

4
只有 name 相同
→ 不合并

5
name 相同但公司不同
→ 不合并
"""
def is_same_lead(a: NormalizedLead,b: NormalizedLead,) -> bool:

    # 1. profile URL 完全一致
    if (a.normalized_profile_url and b.normalized_profile_url):
        return (a.normalized_profile_url == b.normalized_profile_url)

    # 2. 姓名必须一致
    if (not a.normalized_name or not b.normalized_name):
        return False

    if (a.normalized_name != b.normalized_name):
        return False

    # 3. 同姓名 + 同公司
    if (a.normalized_company and b.normalized_company):
        return (a.normalized_company == b.normalized_company)

    # 4. 至少一边公司未知
    return False


# 寻找匹配组
def find_matching_lead_group(lead: NormalizedLead, groups: list[list[NormalizedLead]],) -> int | None:
    matched_groups = []
    for index, group in enumerate(groups):
        if any(
            is_same_lead(
                lead,
                existing
            )
            for existing in group
        ):
            matched_groups.append(index)

    # 只有唯一组命中才合并
    if len(matched_groups) == 1:
        return matched_groups[0]

    # 如果同时疑似匹配多个 group 新建 group
    return None

# 合并
def group_lead_candidates(leads: list[NormalizedLead],) -> list[list[NormalizedLead]]:
    groups: list[list[NormalizedLead]] = []

    for lead in leads:
        group_index = (
            find_matching_lead_group(
                lead,
                groups
            )
        )

        if group_index is None:
            groups.append([lead])

        else:
            groups[
                group_index
            ].append(lead)

    return groups

# evidence去重
def deduplicate_lead_evidence(evidences: list[LeadEvidence],) -> list[LeadEvidence]:
    result: list[LeadEvidence] = []

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

        key = (
            normalized_url,
            normalized_snippet
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(evidence)

    return result

# 通用字符去重
def unique_strings(values: list[str | None],) -> list[str]:

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

# 最终名字选择
def choose_best_lead_name(leads: list[LeadCandidate]) -> str:

    with_profile = [
        lead
        for lead in leads
        if lead.profile_url
    ]

    if with_profile:
        return (
            with_profile[0]
            .name
            .strip()
        )

    return leads[0].name.strip()


# 候选人组合并
def aggregate_lead_group(group: list[NormalizedLead],) -> MergedLead:

    leads = [
        item.original
        for item in group
    ]

    name = choose_best_lead_name(
        leads
    )

    company_names = unique_strings([
        lead.company_name
        for lead in leads
    ])

    titles = unique_strings([
        lead.title
        for lead in leads
    ])

    locations = unique_strings([
        lead.location
        for lead in leads
    ])

    profile_urls = unique_strings([
        normalize_profile_url(
            lead.profile_url
        )
        for lead in leads
    ])

    employment_statuses = (
        unique_strings([
            lead.employment_status
            for lead in leads
        ])
    )

    target_companies = (
        unique_strings([
            lead.target_company
            for lead in leads
        ])
    )

    target_roles = unique_strings([
        lead.target_role
        for lead in leads
    ])

    searched_roles = unique_strings([
        lead.searched_role
        for lead in leads
    ])

    strategy_types = unique_strings([
        lead.strategy_type
        for lead in leads
    ])

    matched_reasons = unique_strings([
        lead.matched_reason
        for lead in leads
    ])

    task_ids = unique_strings([
        lead.task_id
        for lead in leads
    ])

    all_evidence: list[
        LeadEvidence
    ] = []

    for lead in leads:
        all_evidence.extend(
            lead.evidence
        )

    evidence = (
        deduplicate_lead_evidence(
            all_evidence
        )
    )

    return MergedLead(
        name=name,
        company_names=company_names,
        titles=titles,
        locations=locations,
        profile_urls=profile_urls,
        employment_statuses=employment_statuses,
        target_companies=target_companies,
        target_roles=target_roles,
        searched_roles=searched_roles,
        strategy_types=strategy_types,
        matched_reasons=matched_reasons,
        evidence=evidence,
        task_ids=task_ids,
        discovery_count=len(leads),
    )


# 合并候选人
def merge_leads(candidates: list[LeadCandidate],) -> list[MergedLead]:

    # 初步清理
    valid_candidates = [
        lead
        for lead in (
            candidates or []
        )
        if (
            lead is not None
            and lead.name
            and lead.name.strip()
        )
    ]

    if not valid_candidates:
        return []

    # 1 标准化
    normalized = [
        normalize_lead_candidate(
            lead
        )
        for lead in valid_candidates
    ]

    # 2 去重
    groups = group_lead_candidates(
        normalized
    )

    # 3 合并
    merged = [
        aggregate_lead_group(
            group
        )
        for group in groups
    ]

    return merged