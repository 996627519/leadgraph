#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_workflow.py
@Author ：zlh
@Date ：2026-09-14 10:46 
"""
import pytest
from backend.config.settings import Settings
from backend.service.search_service import SearchService
from backend.service.workflow_services import WorkflowServices
from backend.graph.main_graph import run_pipeline, create_graph
from examples.demo_services import DemoModel, DemoSearch


def bundle(settings=None, **model_options):
    settings = settings or Settings()
    provider = DemoSearch()
    return WorkflowServices(settings, SearchService(settings, provider), DemoModel(**model_options)), provider


@pytest.mark.asyncio
async def test_parallel_graph_aggregates_without_shared_input_writes():
    services, provider = bundle()
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == 'completed'
    assert result['target_profile'].original_request == 'fixture'
    assert [x.lead.name for x in result['results']] == ['Alice Jones','Bob Smith','Carol White']
    assert len(result['enriched_leads']) == 3
    assert len(result['merged_company']) == 2
    assert all('fallback' not in q for q in provider.queries)
    assert result['metrics']['physical_calls'] == 10
    assert provider.max_active <= services.settings.search_concurrency
    assert all(x.search_attempts == 2 for x in result['results'])


@pytest.mark.asyncio
@pytest.mark.parametrize('options,status', [({'empty':True},'completed_empty'), ({'missing_roles':True},'needs_input'), ({'fail_schema':'TargetProfile'},'failed')])
async def test_early_termination_is_explicit(options, status):
    services, provider = bundle(**options)
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == status
    assert result['results'] == []
    assert not provider.queries


@pytest.mark.asyncio
async def test_person_fallback_only_after_no_current_candidates():
    services, provider = bundle(primary_empty=True)
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == 'completed'
    assert len([q for q in provider.queries if 'fallback' in q]) == 2


@pytest.mark.asyncio
async def test_budget_exhaustion_keeps_original_leads_and_errors():
    services, _ = bundle(Settings(max_search_calls=4))
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == 'partial'
    assert len(result['results']) == 3
    assert result['metrics']['physical_calls'] == 4
    assert result['metrics']['budget_exhausted']
    assert any(e.error_class == 'BudgetExhausted' for e in result['errors'])


@pytest.mark.asyncio
async def test_enrichment_failure_preserves_candidates():
    services, _ = bundle(fail_schema='EnrichedLeadAssessment')
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == 'partial'
    assert len(result['results']) == 3
    assert all(x.confidence == 0 for x in result['results'])


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [{'max_company_searches':0}, {'max_companies':0}, {'max_person_searches_per_company':0}, {'max_leads_to_enrich':0}])
async def test_zero_limits_finalize(changes):
    services, _ = bundle(Settings(**changes))
    result = await run_pipeline('fixture', services=services)
    assert result['status'] == 'completed_empty'
    assert result['results'] == []


@pytest.mark.asyncio
async def test_zero_enrichment_search_budget_still_analyzes_existing_evidence():
    services, _ = bundle(Settings(max_enrichment_searches=0))
    result = await run_pipeline('fixture', services=services)
    assert len(result['results']) == 3
    assert result['metrics']['physical_calls'] == 4


@pytest.mark.asyncio
async def test_checkpoint_rejects_reusing_completed_thread_as_new_request():
    from langgraph.checkpoint.memory import MemorySaver
    services, _ = bundle(empty=True)
    graph = create_graph(MemorySaver(), services=services, with_outreach=False)
    config = {'configurable': {'thread_id':'fixture'}}
    first = await graph.ainvoke({'user_input':'first'}, config)
    assert first['status'] == 'completed_empty'
    with pytest.raises(ValueError, match='thread'):
        await graph.ainvoke({'user_input':'second'}, config)


@pytest.mark.asyncio
async def test_mixed_zero_and_two_search_workers_join_once():
    class RichAlphaSearch(DemoSearch):
        async def __call__(self, query, **kwargs):
            result = await super().__call__(query, **kwargs)
            if query.startswith('person Alpha'):
                result['results'].append(dict(result['results'][0], url='https://independent.example/alpha'))
            return result
    settings=Settings()
    services=WorkflowServices(settings, SearchService(settings, RichAlphaSearch()), DemoModel())
    result=await run_pipeline('fixture',services=services)
    assert result['status']=='completed'
    assert len(result['results'])==3
    assert [x.search_attempts for x in result['results']]==[0,0,2]
    assert result['metrics']['physical_calls']==6


@pytest.mark.asyncio
async def test_failed_company_worker_does_not_discard_successful_sibling():
    class PartialSearch(DemoSearch):
        async def __call__(self,query,**kwargs):
            if query=='company discovery 1':
                raise RuntimeError('simulated failure')
            return await super().__call__(query,**kwargs)
    settings=Settings()
    services=WorkflowServices(settings, SearchService(settings,PartialSearch()), DemoModel())
    result=await run_pipeline('fixture',services=services)
    assert result['status']=='partial'
    assert len(result['results'])==3
    assert any(e.stage=='company_worker' for e in result['errors'])


