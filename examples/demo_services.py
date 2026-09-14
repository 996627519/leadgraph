#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：demo_services.py
@Author ：zlh
@Date ：2026-09-14 10:47 
"""
import asyncio
import json
from backend.graph.states.target_profile import TargetProfile
from backend.graph.states.company_search_task import CompanySearchPlan, CompanySearchTask
from backend.graph.states.company_graph_state import CompanyCandidateList, CompanyCandidate, CompanyEvidence
from backend.graph.states.company_score_state import CompanyScoreAssessment, ScoreDimension
from backend.graph.states.person_search_state import PersonSearchPlan, PersonSearchTask
from backend.graph.states.person_extract_state import ExtractedLeadCandidateList, ExtractedLeadCandidate
from backend.graph.states.person_graph_state import LeadEvidence
from backend.graph.states.person_enrichment_state import EnrichedLeadAssessment, EnrichmentEvidence
from backend.service.errors import ModelError


class DemoModel:
    def __init__(self, *, empty=False, missing_roles=False, fail_schema=None, primary_empty=False):
        self.calls = 0
        self.empty, self.missing_roles = empty, missing_roles
        self.fail_schema, self.primary_empty = fail_schema, primary_empty

    async def generate(self, schema, messages):
        self.calls += 1
        await asyncio.sleep(.001)
        if schema.__name__ == self.fail_schema:
            raise ModelError('Simulated model failure')
        data = json.loads(messages[-1].content)
        if schema is TargetProfile:
            return TargetProfile(original_request=data['user_input'], countries=['UK'], industries=['Dairy'],
                                 target_roles=[] if self.missing_roles else ['Engineering Manager'])
        if schema is CompanySearchPlan:
            return CompanySearchPlan(tasks=[] if self.empty else [CompanySearchTask(id=str(i), strategy_type='industry_search',
                objective='Discover dairy companies', query=f'company discovery {i}', priority=5-i, expected_signal='Dairy company') for i in range(2)])
        if schema is CompanyCandidateList:
            return CompanyCandidateList(companies=[CompanyCandidate(name=name, website=f'https://{name.lower()}.example',
                description='Dairy company', evidence=[CompanyEvidence(**{k: source[k] for k in ('title','url','snippet')})])
                for name, source in zip(['Alpha', 'Beta'], data['search_results'])])
        if schema is CompanyScoreAssessment:
            dimension = ScoreDimension(score=90, matched=True, reason='Fixture supports fit')
            return CompanyScoreAssessment(industry_fit=dimension, company_type_fit=dimension, geography_fit=dimension,
                capability_fit=dimension, company_size_fit=dimension, hard_constraint_pass=True, confidence=.9, summary='Fixture match')
        if schema is PersonSearchPlan:
            return PersonSearchPlan(tasks=[PersonSearchTask(id=f'{company["name"]}-{phase}', company_name=company['name'],
                target_role='Engineering Manager', searched_role='Engineering Manager', strategy_type='role_family_search',
                objective='Find managers', query=f'person {company["name"]} {phase}', priority=5-i, expected_signal='Named current manager')
                for company in data['companies'] for i, phase in enumerate(['primary','fallback'])])
        if schema is ExtractedLeadCandidateList:
            if self.primary_empty and 'primary' in data['task']['query']:
                return ExtractedLeadCandidateList(leads=[])
            company = data['task']['company_name']
            names = ['Alice Jones', 'Bob Smith'] if company == 'Alpha' else ['Carol White']
            source = data['search_results'][0]
            return ExtractedLeadCandidateList(leads=[ExtractedLeadCandidate(name=name, title='Engineering Manager',
                company_name=company, employment_status='current', profile_url=source['url'],
                evidence=[LeadEvidence(**{k:s[k] for k in ('title','url','snippet')}) for s in data['search_results']]) for name in names])
        if schema is EnrichedLeadAssessment:
            source = (data['search_results'] or data['lead']['evidence'])[0]
            return EnrichedLeadAssessment(current_company=data['lead']['company_names'][0], current_title='Engineering Manager',
                current_employment_status='current', seniority='manager', confidence=.8, summary='Fictional verified fixture',
                evidence=[EnrichmentEvidence(**{k:source[k] for k in ('title','url','snippet')}, evidence_type='employment')])
        raise AssertionError(f'Unsupported demo schema: {schema}')


class DemoSearch:
    def __init__(self):
        self.queries = []
        self.active = 0
        self.max_active = 0

    async def __call__(self, query, **kwargs):
        self.queries.append(query)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(.005)
            if query.startswith('company'):
                return {'results':[{'title':name, 'url':f'https://{name.lower()}.example/about',
                                    'content':f'{name} is a UK Dairy company.'} for name in ['Alpha','Beta']]}
            if query.startswith('person'):
                company = query.split()[1]
                names = 'Alice Jones and Bob Smith' if company == 'Alpha' else 'Carol White'
                return {'results':[{'title':f'{company} Team', 'url':f'https://{company.lower()}.example/team',
                    'content':f'{names} are current Engineering Managers at {company}.', 'score':.9}]}
            name = 'Alice Jones' if 'Alice' in query else 'Bob Smith' if 'Bob' in query else 'Carol White'
            company = 'Beta' if name.startswith('Carol') else 'Alpha'
            domain = company.lower()+'.example' if query.startswith('site:') else 'industry.example'
            return {'results':[{'title':name, 'url':f'https://{domain}/people/{name.replace(" ","-")}',
                'content':f'{name} is a current Engineering Manager at {company}.', 'score':.9}]}
        finally:
            self.active -= 1