#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_rules.py
@Author ：zlh
@Date ：2026-09-14 10:45 
"""
from itertools import permutations
from types import SimpleNamespace as NS
import pytest
from backend.graph.states.person_graph_state import LeadCandidate, LeadEvidence
from backend.graph.states.company_graph_state import CompanyCandidate
from backend.graph.states.person_merge_state import MergedLead
from backend.graph.states.search_result import SearchResult
from backend.graph.states.target_profile import TargetProfile
from backend.graph.utils.person_utils import merge_leads
from backend.graph.utils.company_utils import merge_companies, rank_company, calculate_company_score
from backend.graph.utils.evidence import verify_citations, select_evidence, evidence_sufficient


def test_shared_team_page_does_not_merge_different_people():
    candidates=[LeadCandidate(name=name,company_name='Alpha',profile_url='https://alpha.example/team') for name in ['Alice Jones','Bob Smith']]
    assert len(merge_leads(candidates))==2


def test_same_name_company_different_sources_can_merge():
    candidates=[LeadCandidate(name='Alice Jones',company_name='Alpha',profile_url=url) for url in ['https://alpha.example/alice-jones','https://linkedin.com/in/alice-jones']]
    assert len(merge_leads(candidates))==1


def test_conflicting_personal_profiles_remain_separate():
    candidates=[LeadCandidate(name='Alice Jones',company_name='Alpha',profile_url='https://linkedin.com/in/'+slug) for slug in ['alice-one','alice-two']]
    assert len(merge_leads(candidates))==2


def test_company_merge_is_order_independent_for_ambiguous_domains():
    candidates=[CompanyCandidate(name='Alpha',website='https://a.example'), CompanyCandidate(name='Alpha',website='https://b.example'), CompanyCandidate(name='Alpha')]
    results=[sorted((x.name,x.domain or '',x.discovery_count) for x in merge_companies(list(p))) for p in permutations(candidates)]
    assert all(result==results[0] for result in results)
    assert len(results[0])==3


def test_top_k_respects_cap_and_does_not_replace_high_with_medium():
    from backend.graph.states.company_score_state import CompanyScore, ScoreDimension
    from backend.graph.states.company_graph_state import MergedCompany
    dimension=ScoreDimension(score=90,reason='fixture')
    companies=[CompanyScore(hard_constraint_pass=True,total_score=95-i,confidence=.9,
        company=MergedCompany(domain=str(i),name=str(i)), industry_fit=dimension,company_type_fit=dimension,
        geography_fit=dimension,capability_fit=dimension,company_size_fit=dimension,
        recommendation='high' if 95-i>=80 else 'medium', summary='fixture') for i in range(22)]
    assert len(rank_company(companies,max_companies=2))==2
    assert [x.scored_company.total_score for x in rank_company(companies,max_companies=20)]==list(range(95,75,-1))
    assert not rank_company(companies,max_companies=0)


def test_confidence_threshold_is_enforced():
    item=NS(hard_constraint_pass=True,total_score=99,confidence=.2,company=NS(domain='',name='A'))
    assert rank_company([item])==[]


def test_unspecified_dimensions_do_not_lower_score():
    assessment=NS(industry_fit=NS(score=90),company_type_fit=NS(score=0),geography_fit=NS(score=0),capability_fit=NS(score=0),company_size_fit=NS(score=0))
    assert calculate_company_score(assessment,TargetProfile(original_request='x',industries=['Dairy']))==90


def test_citations_require_real_url_and_literal_excerpt():
    source=SearchResult(url='https://a.example/team',title='Original',snippet='Alice Jones is a manager at Alpha.')
    good=LeadEvidence(url=source.url,title='Invented title',snippet='Alice Jones is a manager')
    fake=LeadEvidence(url='https://fake.example',title='X',snippet=good.snippet)
    paraphrase=good.model_copy(update={'snippet':'Alice runs the whole company'})
    result=verify_citations([good,fake,paraphrase],[source])
    assert len(result)==1 and result[0].title=='Original'


def test_provider_score_alone_cannot_pass_identity_filter():
    lead=MergedLead(name='Alice Jones',company_names=['Alpha'])
    unrelated=SearchResult(url='https://a.example',title='Bob Smith',snippet='Alpha employee',score=.99)
    assert select_evidence(lead,[unrelated])==[]


def test_duplicate_sources_do_not_fill_evidence_slots():
    lead=MergedLead(name='Alice Jones',company_names=['Alpha'])
    a=SearchResult(url='https://a.example/team?utm_source=x',title='Alice Jones Alpha',snippet='Alice Jones at Alpha')
    b=a.model_copy(update={'url':'https://a.example/team'})
    assert len(select_evidence(lead,[a,b]))==1


def test_sufficiency_requires_independent_domains_and_current_status():
    lead=MergedLead(name='Alice Jones',company_names=['Alpha'],titles=['Manager'],employment_statuses=['current'])
    a=LeadEvidence(url='https://a.example/team',title='Alice Jones Alpha',snippet='Alice Jones at Alpha')
    b=a.model_copy(update={'url':'https://a.example/other'})
    c=a.model_copy(update={'url':'https://b.example/profile'})
    assert not evidence_sufficient(lead,[a,b])
    assert evidence_sufficient(lead,[a,c])
    assert not evidence_sufficient(lead.model_copy(update={'employment_statuses':['unclear']}),[a,c])


def test_invalid_size_range_is_rejected():
    with pytest.raises(ValueError): TargetProfile(original_request='x',company_size_min=10,company_size_max=2)
