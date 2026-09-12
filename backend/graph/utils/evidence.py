#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：evidence.py
@Author ：zlh
@Date ：2026-09-11 22:21 
"""
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from backend.graph.states.search_result import SearchResult

TRACKING = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}


# 规范化url
def canonical_url(value):
    if not isinstance(value, str) or not value.strip():
        return ''
    try:
        parts = urlsplit(value.strip())
        if parts.scheme.lower() not in {'http', 'https'} or not parts.hostname or parts.username:
            return ''
        query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if k.casefold() not in TRACKING))
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), query, ''))
    except ValueError:
        return ''


def unique_strings(values):
    seen, result = set(), []
    for value in values:
        if value and value.strip() and value.strip().casefold() not in seen:
            seen.add(value.strip().casefold())
            result.append(value.strip())
    return result


def normalize_location(value):
    return ' '.join(value.casefold().split()) or None if value else None


# 清理搜索结果
def clean_search_results(results):
    best = {}
    for result in results:
        key = canonical_url(result.url)
        if not key or not (result.title.strip() or result.snippet.strip()):
            continue
        previous = best.get(key)
        if previous is None or len(result.snippet) > len(previous.snippet):
            best[key] = result.model_copy(update={'url': key})
    return [best[key] for key in sorted(best)]


# 格式化搜索结果
def parse_tavily_results(response, task_id=None):
    results = []
    for item in response.get('results', []):
        url = canonical_url(item.get('url'))
        if not url:
            continue
        score = item.get('score')
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            score = None
        results.append(SearchResult(url=url, title=str(item.get('title') or ''),
            snippet=str(item.get('content') or '')[:6000], domain=urlsplit(url).hostname,
            provider='tavily', score=score, task_id=task_id))
    return clean_search_results(results)

# 引用核验过滤器，检验提取的结果是否在搜索结果中，防止llm幻觉
def verify_citations(citations, sources):
    by_url = {}
    for source in sources:
        by_url.setdefault(canonical_url(source.url), []).append(source)
    verified = []
    seen = set()
    for item in citations:
        key = canonical_url(item.url)
        excerpt = ' '.join(item.snippet.split())
        for source in by_url.get(key, []):
            if excerpt and excerpt in ' '.join(source.snippet.split()) and (key, excerpt) not in seen:
                seen.add((key, excerpt))
                verified.append(item.model_copy(update={'url': key, 'title': source.title}))
                break
    return verified


"""
对于候选人，在evidence中寻找证据，返回evidence中是否包含name和company
"""
def identity_match(name, companies, result):
    text = ' '.join(f'{result.title} {result.snippet}'.casefold().split())
    name = ' '.join(name.casefold().split())
    name_match = bool(name) and re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text) is not None
    company_match = any(c and c.casefold() in text for c in companies)
    return name_match, company_match

# 挑选出最佳evidence
def select_evidence(lead, results, limit=10):
    scored = []
    companies = lead.company_names or lead.target_companies
    for result in clean_search_results(results):
        name_hit, company_hit = identity_match(lead.name, companies, result)
        if not name_hit:
            continue
        text = f'{result.title} {result.snippet}'.casefold()
        score = 5 + 3 * company_hit + 2 * any(t.casefold() in text for t in lead.titles) + (result.score or 0)
        scored.append((score, result.url, result))
    return [r for _, _, r in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


"""
如果在职状态为current+有公司名+有职位 直接判定为信息充足，可直接跳过
如果evidence中包含了两条及以上证据（名字和公司都支持）则判定为证据充足
"""
def evidence_sufficient(lead, sources):
    if set(lead.employment_statuses) != {'current'} or not lead.company_names or not lead.titles:
        return False
    domains = set()
    for source in sources:
        if all(identity_match(lead.name, lead.company_names, source)):
            url = canonical_url(source.url)
            if url:
                domains.add(urlsplit(url).hostname.removeprefix('www.'))
    return len(domains) >= 2