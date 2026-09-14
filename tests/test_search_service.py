#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_search_service.py
@Author ：zlh
@Date ：2026-09-14 10:45 
"""
import asyncio
import json
import pytest
from backend.config.settings import Settings
from backend.service.search_service import SearchService, normalize_response
from backend.service.errors import SearchError, BudgetExhausted


@pytest.mark.parametrize('wrapper', [lambda x:x, json.dumps, lambda x:[{'type':'text','text':json.dumps(x)}],
    lambda x:{'structuredContent':x}, lambda x:{'content':[{'type':'text','text':json.dumps(x)}]}])
def test_response_shapes(wrapper):
    assert normalize_response(wrapper({'results':[]})) == {'results':[]}


@pytest.mark.parametrize('data', [[], {}, {'isError':True,'results':[]}, {'results':None}, {'results':['bad']}, 'not json'])
def test_invalid_responses_are_not_silent_empty_results(data):
    with pytest.raises(SearchError): normalize_response(data)


@pytest.mark.asyncio
async def test_concurrent_identical_requests_are_coalesced_and_copied():
    calls = []
    async def provider(**kw):
        calls.append(kw)
        await asyncio.sleep(.01)
        return {'results':[{'title':'A'}]}
    service = SearchService(Settings(), provider)
    results = await asyncio.gather(*[service.search('same',run_id='r') for _ in range(10)])
    assert len(calls) == 1
    results[0]['results'].clear()
    assert results[1]['results']
    cached = await service.search('same',run_id='r')
    assert cached['results']
    assert service.metrics('r')['cache_hits'] == 1
    assert service.metrics('r')['coalesced_requests'] == 9


@pytest.mark.asyncio
async def test_physical_budget_is_atomic_under_parallel_requests():
    calls = []
    async def provider(**kw):
        calls.append(kw)
        await asyncio.sleep(.001)
        return {'results':[]}
    service = SearchService(Settings(max_search_calls=3), provider)
    results = await asyncio.gather(*[service.search(str(i),run_id='r') for i in range(20)],return_exceptions=True)
    assert len(calls) == 3
    assert sum(isinstance(x,BudgetExhausted) for x in results) == 17


@pytest.mark.asyncio
async def test_transport_retry_consumes_budget():
    calls = []
    async def provider(**kw):
        calls.append(kw)
        if len(calls)==1: raise ConnectionError('temporary')
        return {'results':[]}
    service = SearchService(Settings(), provider)
    assert await service.search('q',run_id='r') == {'results':[]}
    assert service.metrics('r')['physical_calls'] == 2


@pytest.mark.asyncio
async def test_cache_keys_include_parameters_and_expiration():
    calls=[]
    async def provider(**kw):
        calls.append(kw)
        return {'results':[]}
    service=SearchService(Settings(cache_ttl_seconds=0),provider)
    await service.search('q',run_id='r')
    await service.search('q',run_id='r')
    await service.search('q',run_id='r',max_results=8)
    assert len(calls)==3


@pytest.mark.asyncio
async def test_nontransient_errors_not_retried_or_exposed():
    async def provider(**kw): raise RuntimeError('secret-key-in-url')
    service=SearchService(Settings(),provider)
    with pytest.raises(SearchError,match='RuntimeError') as caught:
        await service.search('q',run_id='r')
    assert 'secret' not in str(caught.value)
    assert service.metrics('r')['physical_calls']==1
